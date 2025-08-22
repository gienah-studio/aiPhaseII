from datetime import datetime, timedelta, date
import random
import json
import os
import redis
from typing import List, Dict, Any, Tuple, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from nanoid import generate

from shared.models.virtual_order_pool import VirtualOrderPool
from shared.models.virtual_order_reports import VirtualOrderReports
from shared.models.tasks import Tasks
from shared.models.userinfo import UserInfo
from shared.models.original_user import OriginalUser
from shared.models.agents import Agents
from shared.exceptions import BusinessException
from ..utils.excel_utils import ExcelProcessor
import math
import logging

logger = logging.getLogger(__name__)

class VirtualOrderService:
    """虚拟订单服务类"""

    # 任务类型权重配置常量
    TASK_TYPE_WEIGHTS = {
        'avatar_redesign': 60,     # 头像改版：60%
        'room_decoration': 20,     # 房间装修：20%
        'photo_extension': 20      # 扩图：20%
    }

    def __init__(self, db: Session, redis_client: Optional[redis.Redis] = None):
        self.db = db
        self.redis_client = redis_client

        # nanoid字符集（对应JS的customAlphabet('1234567890abcdef', 10)）
        self.nanoid_alphabet = '1234567890abcdef'
        self.nanoid_length = 10

        # 加载任务内容配置文件
        self._load_task_content_config()

        # 任务模板配置（后续可以从配置文件或数据库读取）
        self.task_templates = {
            'source': '集团业务',  # 可选：淘宝、集团业务、其他业务
            'commission_unit': '人民币',
            'task_style': '其他',  # 修改为其他
            'task_type': '其他',  # 修改为其他
            'reference_images': '',
            'founder': '虚拟订单系统',
            'founder_id': 0,
            'orders_number': 1,
            'order_received_number': 0,
            'status': '0',  # 修改为数字状态
            'payment_status': '1',  # 待支付
            'task_level': 'D',  # 修改为D级别
            'end_date_hours': 3,  # 接单截止时间：创建后3小时
            'delivery_date_hours': 3,  # 交稿时间：接单后3小时
        }

        # 初始化分配器和管理器（延迟加载，避免循环导入）
        self._allocator = None
        self._service_manager = None

    @property
    def allocator(self):
        """获取任务分配器实例"""
        if self._allocator is None:
            from .virtual_task_allocator import VirtualTaskAllocator
            self._allocator = VirtualTaskAllocator(self.db, self.redis_client)
        return self._allocator

    @property
    def service_manager(self):
        """获取虚拟客服管理器实例"""
        if self._service_manager is None:
            from .virtual_customer_service_manager import VirtualCustomerServiceManager
            self._service_manager = VirtualCustomerServiceManager(self.db, self.redis_client)
        return self._service_manager

    def _load_task_content_config(self):
        """加载任务内容配置文件"""
        try:
            # 获取配置文件目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_dir = os.path.join(current_dir, '..', 'config')

            # 加载标题配置（使用新版分类配置）
            titles_file = os.path.join(config_dir, 'task_titles_new.json')
            with open(titles_file, 'r', encoding='utf-8') as f:
                self.task_titles_data = json.load(f)

            # 加载背景配置（使用新版分类配置）
            backgrounds_file = os.path.join(config_dir, 'task_backgrounds.json')
            with open(backgrounds_file, 'r', encoding='utf-8') as f:
                self.task_backgrounds_data = json.load(f)

            # 加载风格配置（使用新版分类配置）
            styles_file = os.path.join(config_dir, 'task_styles.json')
            with open(styles_file, 'r', encoding='utf-8') as f:
                self.task_styles_data = json.load(f)

            # 加载分层模板配置
            templates_file = os.path.join(config_dir, 'task_templates.json')
            with open(templates_file, 'r', encoding='utf-8') as f:
                self.task_templates_data = json.load(f)

            # 加载具体头像风格配置
            avatar_styles_file = os.path.join(config_dir, 'avatar_styles_specific.json')
            with open(avatar_styles_file, 'r', encoding='utf-8') as f:
                self.avatar_styles_specific = json.load(f)

        except Exception as e:
            # 如果加载失败，使用默认配置
            print(f"警告：加载任务内容配置文件失败: {str(e)}")
            self.task_titles_data = {
                'avatar_redesign': ["制作专业商务头像设计"],
                'room_decoration': ["毛坯房现代简约风格设计"],
                'photo_extension': ["半身照扩展为全身照效果"]
            }
            self.task_backgrounds = ["梦幻的场景中"]
            self.task_styles = ["水彩手绘风格，柔和的色彩晕染"]
            self.task_templates_data = None
            self.avatar_styles_specific = None

    def generate_order_number(self) -> str:
        """生成订单号"""
        return generate(self.nanoid_alphabet, self.nanoid_length)

    def generate_random_task_content(self) -> Dict[str, str]:
        """
        生成随机的任务内容，基于60:20:20比例控制

        Returns:
            Dict[str, str]: 包含summary、requirement和task_type的字典
        """
        # 先按权重选择任务类型
        task_type = self._select_task_type_by_weight()

        # 根据类型生成内容
        return self.generate_task_content_by_type(task_type)

    def _select_task_type_by_weight(self, custom_weights: Dict[str, int] = None) -> str:
        """
        根据权重配置随机选择任务类型

        Args:
            custom_weights: 自定义权重配置，如果为None则使用默认权重

        Returns:
            str: 选中的任务类型
        """
        # 使用自定义权重或默认权重
        weights = custom_weights if custom_weights is not None else self.TASK_TYPE_WEIGHTS

        # 计算累积权重
        cumulative_weights = []
        task_types = []
        total_weight = 0

        for task_type, weight in weights.items():
            total_weight += weight
            cumulative_weights.append(total_weight)
            task_types.append(task_type)

        # 生成随机数
        random_value = random.randint(1, total_weight)

        # 选择对应的任务类型
        for i, cumulative_weight in enumerate(cumulative_weights):
            if random_value <= cumulative_weight:
                return task_types[i]

        # 兜底返回第一个类型
        return task_types[0] if task_types else 'avatar_redesign'

    def generate_task_content_by_type(self, task_type: str) -> Dict[str, str]:
        """
        根据指定类型生成任务内容

        Args:
            task_type: 任务类型

        Returns:
            Dict[str, str]: 包含summary、requirement和task_type的字典
        """
        try:
            # 获取该类型的标题
            title = self._get_title_by_task_type(task_type)

            # 对于头像改版，100%使用具体风格生成
            if task_type == 'avatar_redesign':
                # 100% 使用具体风格描述，确保符合客户要求
                requirement = self._generate_specific_avatar_requirement()
            else:
                # 其他类型使用原有方式
                requirement = self._generate_requirement_by_type(task_type)

            return {
                'summary': title,
                'requirement': requirement,
                'task_type': task_type
            }

        except Exception as e:
            logger.warning(f"按类型生成任务内容失败: {str(e)}, 使用默认方式")
            # 失败时使用原有方式
            if self.task_templates_data and random.random() < 0.3:
                return self._generate_template_based_content()
            else:
                return self._generate_simple_content()

    def _get_title_by_task_type(self, task_type: str) -> str:
        """
        根据任务类型获取对应的标题

        Args:
            task_type: 任务类型

        Returns:
            str: 任务标题
        """
        title_mapping = {
            'avatar_redesign': [
                '生成宫崎骏风格头像',
                '生成二次元风格头像',
                '生成虚拟头像',
                '生成国风头像',
                '生成科技感头像',
                '生成卡通风格头像',
                '生成小清新风格头像',
                '生成光影感强的头像',
                '生成手绘风格头像',
                '生成美颜后的头像',
                '生成艺术照风格感的头像',
                '生成POP风格头像',
                '生成赛博朋克风格头像',
                '制作精美的虚拟人物形象',
                '绘制具有表现力的角色头像',
                '创作个性化角色头像设计'
            ],
            'room_decoration': [
                '设计温馨舒适的室内空间',
                '创作现代简约风格的房间装修',
                '制作个性化的室内装饰方案',
                '设计功能与美观并重的居住空间',
                '打造理想的家居环境设计',
                '创建舒适的室内生活空间'
            ],
            'photo_extension': [
                '扩展照片展现完整画面',
                '补全图像缺失的部分内容',
                '扩充图片边界展示更多细节',
                '延伸画面呈现完整构图',
                '补充图像周边环境内容',
                '扩展视觉范围创造完整场景'
            ]
        }

        # 如果没有找到对应类型，使用默认标题
        if task_type not in title_mapping:
            # 从新配置中获取默认标题
            default_titles = []
            if hasattr(self, 'task_titles_data') and self.task_titles_data:
                for category_titles in self.task_titles_data.values():
                    default_titles.extend(category_titles[:5])  # 每类取前5个
            if not default_titles:
                default_titles = ["制作专业商务头像设计"]
            titles = default_titles
        else:
            titles = title_mapping.get(task_type)
        return random.choice(titles)

    def _generate_specific_avatar_requirement(self) -> str:
        """
        生成具体的头像风格需求描述

        Returns:
            str: 具体的头像需求描述
        """
        if not hasattr(self, 'avatar_styles_specific') or not self.avatar_styles_specific:
            # 如果没有加载具体风格配置，使用大规模组合方式
            return self._generate_large_scale_avatar_requirement()

        try:
            # 从具体风格配置中随机选择
            style_combinations = self.avatar_styles_specific.get('style_combinations', [])
            specific_styles = self.avatar_styles_specific.get('specific_styles', {})

            if not style_combinations:
                return self._generate_large_scale_avatar_requirement()

            # 随机选择一个风格组合
            style_combo = random.choice(style_combinations)
            style_name = style_combo['style']
            template = style_combo['template']

            # 获取该风格的具体配置
            style_config = specific_styles.get(style_name, {})

            # 随机选择技法、色彩和特征
            technique = random.choice(style_config.get('techniques', ['专业处理']))
            color = random.choice(style_config.get('colors', ['协调色彩']))
            feature = random.choice(style_config.get('features', ['精美效果']))

            # 格式化模板
            return template.format(
                technique=technique,
                color=color,
                feature=feature
            )

        except Exception as e:
            # 如果出错，回退到大规模组合方式
            logger.warning(f"生成具体头像风格描述失败: {str(e)}")
            return self._generate_large_scale_avatar_requirement()

    def _generate_large_scale_avatar_requirement(self) -> str:
        """
        生成大规模组合的头像风格需求描述，专注于头像改版相关的技法

        Returns:
            str: 头像改版的需求描述
        """
        # 头像风格库（客户要求的具体风格为主）
        styles = [
            # 客户要求的13种基础风格
            '宫崎骏风格', '二次元风格', '虚拟头像', '国风', '科技感',
            '卡通风格', '小清新风格', '光影感强', '手绘风格', '美颜后',
            '艺术照风格', 'POP风格', '赛博朋克风格',
            # 相关绘画风格扩展
            '水彩风格', '油画风格', '素描风格', '像素风格', '蒸汽波风格',
            '动漫风格', 'Q版风格', '日系风格', '萌系风格', '治愈系风格',
            '欧美风格', '韩系风格', '复古风格', '现代风格', '简约风格'
        ]

        # 头像处理技法库（专注于图像处理和绘画技法）
        techniques = [
            '线条处理', '色彩调整', '风格转换', '细节优化', '特征保持',
            '比例调整', '光影渲染', '质感提升', '美颜处理', '笔触表现',
            '水彩渲染', '油画厚涂', '素描勾勒', '数字绘制', '手绘技法',
            '面部重塑', '五官优化', '肌肤美化', '发型设计', '表情调整',
            '眼部处理', '鼻部调整', '嘴部优化', '脸型修饰', '轮廓强化'
        ]

        # 色彩搭配库
        colors = [
            '暖色调', '冷色调', '中性色', '高饱和度', '低饱和度',
            '明亮色调', '渐变色彩', '单色调', '对比色彩', '柔和色系',
            '鲜艳色彩', '淡雅色调', '复古色系', '现代色彩', '自然色调',
            '粉嫩色系', '清新色调', '浓郁色彩', '淡雅配色', '和谐色调'
        ]

        # 效果特征库
        features = [
            '精美效果', '自然美感', '艺术气息', '专业质感', '视觉冲击',
            '温暖感觉', '清新氛围', '神秘魅力', '现代感', '复古韵味',
            '梦幻效果', '立体层次', '细腻质感', '生动表现', '和谐统一',
            '可爱魅力', '优雅气质', '时尚感', '个性特色', '独特风采'
        ]

        # 随机选择组合
        style = random.choice(styles)
        technique = random.choice(techniques)
        color = random.choice(colors)
        feature = random.choice(features)

        # 模板库
        templates = [
            f'生成{style}头像：采用{technique}技法，运用{color}色彩，展现{feature}，打造专业效果',
            f'制作{style}头像：使用{technique}处理，配合{color}色调，体现{feature}，呈现精美作品',
            f'设计{style}头像：通过{technique}技术，采用{color}配色，突出{feature}，营造独特风格',
            f'绘制{style}头像：运用{technique}手法，使用{color}色彩，展现{feature}，体现艺术美感',
            f'创作{style}头像：采用{technique}效果，配合{color}色调，营造{feature}，呈现专业水准'
        ]

        return random.choice(templates)

    def _generate_requirement_by_type(self, task_type: str) -> str:
        """
        根据任务类型生成对应的需求描述

        Args:
            task_type: 任务类型

        Returns:
            str: 需求描述
        """
        # 基础描述模板 - 更具体化的描述
        base_templates = {
            'avatar_redesign': [
                '生成{style}头像：将人物头像转换为{style}，保持面部特征和辨识度，使用{technique}处理细节，采用{color}色彩方案，确保风格转换自然流畅',
                '制作{style}头像：创作具有{style}特色的人物头像，通过{technique}优化画面效果，运用{color}统一色调，突出风格特点',
                '设计{style}头像：打造{style}的人物形象，采用{technique}技术处理，使用{color}配色，营造独特的视觉效果',
                '绘制{style}头像：创建富有{style}特色的角色形象，运用{technique}技法，配合{color}色调，展现风格魅力',
                '生成{style}人物头像：制作具有{style}风格特征的头像作品，通过{technique}处理，采用{color}色彩搭配，呈现专业效果'
            ],
            'room_decoration': [
                '装修风格：设计{style}风格室内空间，重点处理{technique}，使用{color}作为主色调，确保空间功能合理，整体效果统一',
                '装修风格：制作{style}风格装修方案，着重{technique}设计，采用{color}配色方案，注重实用性和美观性的平衡',
                '装修风格：规划{style}风格室内设计，优化{technique}布局，运用{color}色彩搭配，满足居住需求和审美要求'
            ],
            'photo_extension': [
                '照片扩图：扩展图片边界，补全背景内容，保持原有{style}风格和{color}色彩连贯性，使用{technique}确保扩展部分与原图自然衔接',
                '照片扩图：延伸画面范围，填充周边区域，维持{style}构图风格，采用{technique}处理方式，确保{color}色调统一协调',
                '照片扩图：补充图像边缘内容，完善整体画面，延续{style}视觉风格，运用{technique}技术，保持{color}色彩一致性'
            ]
        }

        # 针对不同任务类型的专用变量池
        if task_type == 'avatar_redesign':
            # 扩展具体风格库，包含客户要求的具体风格
            styles = [
                '宫崎骏风格', '二次元风格', '虚拟头像', '国风', '科技感',
                '卡通风格', '小清新风格', '光影感强', '手绘风格', '美颜后',
                '艺术照风格', 'POP风格', '赛博朋克风格', '动漫', 'Q版',
                '日系', '萌系', '治愈系', '水彩风格', '油画风格', '素描风格',
                '像素风格', '蒸汽波风格', '复古风格', '未来科幻风格'
            ]
            moods = ['清晰', '柔和', '鲜明', '自然', '简洁', '精致', '生动', '和谐', '梦幻', '唯美', '酷炫', '温暖']
            techniques = ['线条处理', '色彩调整', '风格转换', '细节优化', '特征保持', '比例调整', '光影渲染', '质感提升', '美颜处理']
            colors = ['暖色调', '冷色调', '中性色', '高饱和度', '低饱和度', '明亮色调', '渐变色彩', '单色调', '对比色彩']
            characters = ['头像', '人物', '形象', '角色', '画面主体', '目标对象']
        elif task_type == 'room_decoration':
            styles = ['现代简约', '北欧风格', '新中式', '美式乡村', '工业风格', '地中海风格']
            moods = ['实用', '舒适', '简洁', '温馨', '明亮', '宽敞', '整洁', '协调']
            techniques = ['空间布局', '色彩搭配', '材质选择', '灯光设计', '家具配置', '收纳设计']
            colors = ['暖色调', '冷色调', '中性色', '木色系', '白色系', '灰色系']
            characters = ['空间', '房间', '居室', '环境', '区域', '场所']
        else:  # photo_extension
            styles = ['原有风格', '自然风格', '简约风格', '写实风格', '清新风格', '现代风格']
            moods = ['自然', '连贯', '统一', '协调', '平衡', '流畅', '完整', '真实']
            techniques = ['边界扩展', '内容填充', '色彩匹配', '纹理延续', '光影处理', '透视校正']
            colors = ['原图色调', '相近色系', '渐变过渡', '色温匹配', '饱和度统一', '明暗协调']
            characters = ['画面', '场景', '图像', '构图', '背景', '环境']

        # 获取对应模板
        templates = base_templates.get(task_type, base_templates['avatar_redesign'])
        template = random.choice(templates)

        # 随机选择变量
        style = random.choice(styles)
        mood = random.choice(moods)
        technique = random.choice(techniques)
        color = random.choice(colors)
        character = random.choice(characters)

        # 格式化模板
        try:
            return template.format(
                style=style,
                mood=mood,
                technique=technique,
                color=color,
                character=character
            )
        except KeyError:
            # 如果格式化失败，返回简化版本
            return f"{style}风格，{mood}氛围，{technique}，{color}"

    def _generate_simple_content(self) -> Dict[str, str]:
        """使用原有的简单组合方式生成内容"""
        # 随机选择任务类型
        task_types = ['avatar_redesign', 'room_decoration', 'photo_extension']
        task_type = random.choice(task_types)

        # 根据任务类型选择标题
        if hasattr(self, 'task_titles_data') and self.task_titles_data and task_type in self.task_titles_data:
            titles = self.task_titles_data[task_type][:10]  # 取前10个
        else:
            titles = ["制作专业商务头像设计", "毛坯房现代简约风格设计", "半身照扩展为全身照效果"]
        title = random.choice(titles)

        # 根据任务类型选择背景和风格
        if hasattr(self, 'task_backgrounds_data') and self.task_backgrounds_data and task_type in self.task_backgrounds_data:
            background = random.choice(self.task_backgrounds_data[task_type])
        else:
            background = "在温馨的环境中"

        if hasattr(self, 'task_styles_data') and self.task_styles_data and task_type in self.task_styles_data:
            style = random.choice(self.task_styles_data[task_type])
        else:
            style = "现代简约风格"

        # 添加随机修饰元素
        modifiers = []
        if self.task_templates_data and 'detail_modifiers' in self.task_templates_data:
            detail_modifiers = self.task_templates_data['detail_modifiers']
            # 20%概率添加时间元素
            if random.random() < 0.2:
                modifiers.append(random.choice(detail_modifiers['time_elements']))
            # 15%概率添加天气元素
            if random.random() < 0.15:
                modifiers.append(random.choice(detail_modifiers['weather_elements']))
            # 25%概率添加情感元素
            if random.random() < 0.25:
                modifiers.append(random.choice(detail_modifiers['emotion_elements']))

        # 组合生成需求描述
        modifier_text = "，".join(modifiers) + "，" if modifiers else ""
        requirement = f"{background}，{modifier_text}{style}"

        return {
            'summary': title,
            'requirement': requirement,
            'task_type': task_type  # 返回实际选择的任务类型
        }

    def _generate_template_based_content(self) -> Dict[str, str]:
        """使用分层模板生成更智能的内容组合"""
        themes = self.task_templates_data['themes']
        art_styles = self.task_templates_data['art_styles']
        combination_rules = self.task_templates_data['combination_rules']

        # 选择主题
        theme_name = random.choice(list(themes.keys()))
        theme_data = themes[theme_name]

        # 选择艺术风格
        art_style_name = random.choice(list(art_styles.keys()))
        art_style_data = art_styles[art_style_name]

        # 检查是否为推荐组合
        is_compatible = any(
            theme_name in combo and art_style_name in combo
            for combo in combination_rules.get('highly_compatible', [])
        )

        # 生成角色和场景
        character = random.choice(theme_data['characters'])
        scene = random.choice(theme_data['scenes'])
        mood = random.choice(theme_data['moods'])
        color = random.choice(theme_data['colors'])

        # 生成技法和效果
        technique = random.choice(art_style_data['techniques'])
        effect = random.choice(art_style_data['effects'])

        # 生成标题
        title = f"创作{theme_name}风格的{character}角色设计"

        # 生成描述
        requirement = f"{scene}中，{mood}的{character}形象，采用{art_style_name}技法，{technique}表现，{color}为主色调，突出{effect}的视觉效果"

        return {
            'summary': title,
            'requirement': requirement,
            'task_type': 'template'  # 模板内容标记为模板类型
        }

    def calculate_task_amounts(self, total_amount: Decimal) -> List[Decimal]:
        """
        计算任务金额分配

        第一阶段：使用5、10、15、20、25随机分配
        第二阶段：剩余金额用价值回收规则处理（仅适用于价值回收场景）
        - 剩余金额 ≥ 8元 → 生成10元任务
        - 剩余金额 < 8元 → 生成5元任务

        Args:
            total_amount: 总补贴金额

        Returns:
            List[Decimal]: 任务金额列表
        """
        amounts = []
        remaining = total_amount

        # 如果金额为0，不生成任务
        if remaining <= 0:
            return []

        # 如果金额小于10元，按8元规则处理
        if remaining < 10:
            if remaining >= 8:
                return [Decimal('10')]
            else:
                return [Decimal('5')]

        # 固定的金额选项：5, 10, 15, 20, 25
        available_amounts = [Decimal('5'), Decimal('10'), Decimal('15'), Decimal('20'), Decimal('25')]

        # 第一阶段：随机生成5-25之间的5的倍数任务
        while remaining > 0:
            if remaining <= Decimal('5'):
                # 剩余金额小于等于5元，作为最后一个任务
                amounts.append(remaining)
                break
            elif remaining < Decimal('10'):
                # 剩余金额小于10元，按价值回收规则处理
                if remaining >= 8:
                    # 剩余金额 ≥ 8元，生成10元任务
                    amounts.append(Decimal('10'))
                else:
                    # 剩余金额 < 8元，生成5元任务
                    amounts.append(Decimal('5'))
                break
            else:
                # 从可用金额中筛选不超过剩余金额的选项
                possible_amounts = [amount for amount in available_amounts if amount <= remaining]

                if not possible_amounts:
                    # 如果没有合适的金额选项，按价值回收规则处理剩余金额
                    if remaining >= 8:
                        amounts.append(Decimal('10'))
                    else:
                        amounts.append(Decimal('5'))
                    break

                # 随机选择一个金额
                selected_amount = random.choice(possible_amounts)
                amounts.append(selected_amount)
                remaining -= selected_amount

        return amounts

    def calculate_on_demand_task_amounts(self, total_amount: Decimal) -> List[Decimal]:
        """
        按需生成任务金额分配（生成1-2个任务）

        Args:
            total_amount: 可用金额

        Returns:
            List[Decimal]: 任务金额列表（1-2个任务）
        """
        amounts = []

        # 如果金额为0，不生成任务
        if total_amount <= 0:
            return []

        # 如果金额小于5元，生成等额任务
        if total_amount < Decimal('5'):
            return [total_amount]

        # 如果金额小于10元，按8元规则处理
        if total_amount < Decimal('10'):
            if total_amount >= Decimal('8'):
                return [Decimal('10')]
            else:
                return [Decimal('5')]

        # 固定的金额选项：5, 10, 15, 20, 25
        available_amounts = [Decimal('5'), Decimal('10'), Decimal('15'), Decimal('20'), Decimal('25')]

        # 筛选不超过总金额的选项
        possible_amounts = [amount for amount in available_amounts if amount <= total_amount]

        if not possible_amounts:
            # 如果没有合适的金额选项，按规则处理
            if total_amount >= Decimal('8'):
                return [Decimal('10')]
            else:
                return [Decimal('5')]

        # 随机决定生成1个还是2个任务
        task_count = random.choice([1, 2])

        if task_count == 1:
            # 生成1个任务
            selected_amount = random.choice(possible_amounts)
            amounts.append(selected_amount)
        else:
            # 生成2个任务
            first_amount = random.choice(possible_amounts)
            amounts.append(first_amount)

            # 计算剩余金额
            remaining = total_amount - first_amount

            # 为第二个任务选择金额
            if remaining <= Decimal('0'):
                # 剩余金额不足，只生成一个任务
                pass
            elif remaining < Decimal('5'):
                # 剩余金额小于5元，生成等额任务
                amounts.append(remaining)
            elif remaining < Decimal('10'):
                # 剩余金额小于10元，按8元规则处理
                if remaining >= Decimal('8'):
                    amounts.append(Decimal('10'))
                else:
                    amounts.append(Decimal('5'))
            else:
                # 从可用金额中选择不超过剩余金额的选项
                second_possible_amounts = [amount for amount in available_amounts if amount <= remaining]
                if second_possible_amounts:
                    second_amount = random.choice(second_possible_amounts)
                    amounts.append(second_amount)
                else:
                    # 如果没有合适的选项，按规则处理
                    if remaining >= Decimal('8'):
                        amounts.append(Decimal('10'))
                    else:
                        amounts.append(Decimal('5'))

        return amounts

    def create_virtual_task(self, student_id: int, student_name: str, amount: Decimal) -> Optional[Tasks]:
        """
        创建单个虚拟任务

        Args:
            student_id: 学生ID
            student_name: 学生姓名
            amount: 任务金额

        Returns:
            Tasks: 创建的任务对象
        """
        now = datetime.now()

        # 生成随机任务内容
        task_content = self.generate_random_task_content()

        # 尝试从资源库获取参考图片（必须获取到才能创建任务）
        image_info = self._get_reference_image_for_task(task_content)

        # 如果没有获取到参考图片，尝试备用策略
        if not image_info:
            original_task_type = task_content.get('task_type', 'unknown')
            logger.warning(f"无法为任务类型 {original_task_type} 获取参考图片，尝试备用策略")

            # 如果是照片扩图类型没有图片，则只生成头像改版或装修风格
            if original_task_type == 'photo_extension':
                logger.info("照片扩图没有可用图片，改为生成头像改版或装修风格任务")
                # 重新生成任务内容，排除照片扩图
                task_content = self._generate_fallback_task_content()
                image_info = self._get_reference_image_for_task(task_content)

                if not image_info:
                    logger.warning(f"备用策略也无法获取图片，停止创建任务")
                    return None
            else:
                logger.warning(f"无法为任务类型 {original_task_type} 获取参考图片，停止创建任务")
                return None

        # 提取图片URL和ID
        if isinstance(image_info, dict):
            reference_image_url = image_info['file_url']
            image_id = image_info['image_id']
            original_filename = image_info.get('original_filename')
        else:
            # 兼容旧的返回格式
            reference_image_url = image_info
            image_id = None
            original_filename = None

        # 如果是装修风格任务且有原始文件名，提取房间类型并重新生成任务内容
        if task_content.get('task_type') == 'room_decoration' and original_filename:
            room_type = self._extract_room_type_from_filename(original_filename)
            if room_type:
                # 重新生成包含房间类型的任务内容
                task_content = self._generate_room_decoration_content_with_room_type(room_type)
                logger.info(f"根据图片文件名 {original_filename} 提取到房间类型: {room_type}，重新生成任务内容")

        task = Tasks(
            summary=task_content['summary'],
            requirement=task_content['requirement'],
            reference_images=json.dumps([reference_image_url]) if reference_image_url else '',
            source=self.task_templates['source'],
            order_number=self.generate_order_number(),
            commission=amount,
            commission_unit=self.task_templates['commission_unit'],
            end_date=now + timedelta(hours=self.task_templates['end_date_hours']),  # 3小时后过期
            delivery_date=now + timedelta(hours=self.task_templates['delivery_date_hours']),  # 接单后3小时交稿
            status=self.task_templates['status'],
            task_style=self.task_templates['task_style'],
            task_type=self.task_templates['task_type'],
            created_at=now,
            updated_at=now,
            orders_number=self.task_templates['orders_number'],
            order_received_number=self.task_templates['order_received_number'],
            founder=self.task_templates['founder'],
            founder_id=self.task_templates['founder_id'],
            payment_status=self.task_templates['payment_status'],
            task_level=self.task_templates['task_level'],
            is_virtual=True,  # 标识为虚拟任务
            is_renew='0',
            target_student_id=student_id  # 限制只有指定学生可以接取
        )

        # 保存任务到数据库以获取task_id
        self.db.add(task)
        self.db.flush()  # 获取task_id但不提交事务

        # 如果有图片ID，立即标记为已使用
        if image_id:
            try:
                from services.resource_service.service.resource_service import ResourceService
                resource_service = ResourceService(self.db)
                resource_service.mark_image_as_used(image_id, task.id)
                logger.info(f"任务 {task.id} 的图片 {image_id} 已标记为使用")
            except Exception as e:
                logger.error(f"标记图片 {image_id} 为已使用失败: {str(e)}")
                # 回滚任务创建
                self.db.rollback()
                return None

        return task

    def get_student_rebate_rate(self, student_id: int) -> Decimal:
        """
        获取学生的返佣比例

        Args:
            student_id: 学生ID（roleId）

        Returns:
            Decimal: 返佣比例（如0.6表示60%）
        """
        # 查询学生信息
        student = self.db.query(UserInfo).filter(
            UserInfo.roleId == student_id
        ).first()

        if not student or not student.agentId:
            return Decimal('0.6')  # 默认返佣比例60%

        # 查询代理信息
        agent = self.db.query(Agents).filter(
            Agents.id == student.agentId
        ).first()

        if not agent or not agent.agent_rebate:
            return Decimal('0.6')  # 默认返佣比例60%

        # 处理返佣比例字符串
        rebate_str = agent.agent_rebate.replace('%', '') if '%' in agent.agent_rebate else agent.agent_rebate
        try:
            rebate_value = float(rebate_str)
            # 如果值大于1，说明是百分比形式（如60），需要除以100
            if rebate_value > 1:
                return Decimal(str(rebate_value / 100))
            else:
                return Decimal(str(rebate_value))
        except:
            return Decimal('0.6')  # 解析失败时使用默认值

    def generate_virtual_tasks_for_student(self, student_id: int, student_name: str,
                                         subsidy_amount: Decimal, on_demand: bool = False) -> List[Tasks]:
        """
        为学生生成虚拟任务

        Args:
            student_id: 学生ID
            student_name: 学生姓名
            subsidy_amount: 可用补贴金额
            on_demand: 是否按需生成（True=生成1-2个任务，False=全部生成）

        Returns:
            List[Tasks]: 生成的任务列表
        """
        # 任务面值 = 补贴金额
        total_face_value = subsidy_amount

        # 根据模式选择不同的金额分配策略
        if on_demand:
            # 按需生成：只生成1-2个任务
            task_amounts = self.calculate_on_demand_task_amounts(total_face_value)
        else:
            # 传统模式：生成所有任务
            task_amounts = self.calculate_task_amounts(total_face_value)

        # 创建任务（如果图片不足则停止生成）
        tasks = []
        for amount in task_amounts:
            task = self.create_virtual_task(student_id, student_name, amount)
            if task is None:
                logger.warning(f"图片资源不足，停止为学生 {student_name} 生成虚拟任务")
                break
            tasks.append(task)

        return tasks

    def generate_on_demand_virtual_tasks_for_student(self, student_id: int, student_name: str,
                                                   available_amount: Decimal) -> List[Tasks]:
        """
        按需为学生生成虚拟任务（生成1-2个任务）

        Args:
            student_id: 学生ID
            student_name: 学生姓名
            available_amount: 可用金额

        Returns:
            List[Tasks]: 生成的任务列表
        """
        return self.generate_virtual_tasks_for_student(student_id, student_name, available_amount, on_demand=True)

    def _generate_fallback_task_content(self) -> Dict[str, str]:
        """
        生成备用任务内容（排除照片扩图，只生成头像改版和装修风格）

        Returns:
            Dict[str, str]: 包含summary、requirement和task_type的字典
        """
        # 备用任务类型权重（排除照片扩图）
        fallback_weights = {
            'avatar_redesign': 75,     # 头像改版：75%
            'room_decoration': 25      # 房间装修：25%
        }

        # 按权重选择任务类型
        task_type = self._select_task_type_by_weight(fallback_weights)

        # 根据类型生成内容
        return self.generate_task_content_by_type(task_type)

    def import_student_subsidy_data(self, student_data: List[Dict], import_batch: str) -> Dict[str, Any]:
        """
        导入学生每日补贴数据并生成虚拟任务

        Args:
            student_data: 学生数据列表（包含每日补贴额度）
            import_batch: 导入批次号

        Returns:
            Dict: 导入结果统计
        """
        try:
            total_students = 0
            total_subsidy = Decimal('0')
            total_generated_tasks = 0

            for data in student_data:
                student_name = data['student_name']
                subsidy_amount = data['subsidy_amount']

                # 查找学生ID（这里需要根据实际业务逻辑调整）
                # 暂时使用学生姓名作为标识，实际应该有更准确的匹配方式
                student_info = self.db.query(UserInfo).filter(
                    UserInfo.name == student_name,
                    UserInfo.level == '3',  # 学生级别
                    UserInfo.isDeleted == False
                ).first()

                if not student_info:
                    # 如果找不到学生，可以选择跳过或创建新记录
                    # 这里暂时跳过
                    continue

                # 检查是否已存在该学生的补贴池（只查询未删除的记录）
                existing_pool = self.db.query(VirtualOrderPool).filter(
                    VirtualOrderPool.student_id == student_info.roleId,
                    VirtualOrderPool.is_deleted == False
                ).first()

                if existing_pool:
                    # 初始化任务生成标记
                    should_generate_tasks = True

                    # 检查是否为0元补贴（用于删除学生）
                    if subsidy_amount == Decimal('0'):
                        # 0元补贴：执行硬删除，彻底清理该学生的补贴池
                        self.db.delete(existing_pool)
                        logger.info(f"学生 {student_name} 导入0元补贴，已执行硬删除")
                        pool = None  # 标记为已删除，后续不生成任务
                        should_generate_tasks = False
                    elif existing_pool.total_subsidy == subsidy_amount:
                        # 相同金额：只更新导入批次，保持数据完整性，不清理任务，不生成新任务
                        existing_pool.import_batch = import_batch
                        existing_pool.updated_at = datetime.now()
                        logger.info(f"学生 {student_name} 重复导入相同金额 {subsidy_amount}，仅更新导入批次，保持数据完整性")
                        pool = existing_pool  # 使用现有补贴池
                        should_generate_tasks = False  # 标记不生成新任务
                    else:
                        # 不同金额：清理旧任务，更新现有补贴池（以最新补贴金额为准，重置数据）
                        # 清理该学生之前的未完成虚拟任务（避免重复任务）
                        pending_tasks = self.db.query(Tasks).filter(
                            and_(
                                Tasks.is_virtual.is_(True),
                                Tasks.target_student_id == student_info.roleId,
                                Tasks.status.in_(['0'])  # 只删除待接取的任务
                            )
                        ).all()

                        for task in pending_tasks:
                            # 清理图片引用，避免外键约束错误
                            try:
                                from shared.models.resource_images import ResourceImages
                                self.db.query(ResourceImages).filter(
                                    ResourceImages.used_in_task_id == task.id
                                ).update({
                                    'used_in_task_id': None,
                                    'updated_at': datetime.now()
                                })
                                self.db.flush()
                            except Exception as img_error:
                                logger.warning(f"清理任务 {task.id} 的图片引用失败: {str(img_error)}")

                            self.db.delete(task)

                        existing_pool.total_subsidy = subsidy_amount  # 使用最新的补贴金额
                        existing_pool.remaining_amount = subsidy_amount  # 重置剩余金额为最新补贴金额
                        existing_pool.allocated_amount = subsidy_amount  # 重置已分配金额为最新补贴金额
                        existing_pool.completed_amount = Decimal('0')  # 重置已完成金额
                        existing_pool.consumed_subsidy = Decimal('0')  # 重置实际消耗补贴
                        existing_pool.import_batch = import_batch
                        existing_pool.updated_at = datetime.now()
                        existing_pool.last_allocation_at = datetime.now()
                        logger.info(f"学生 {student_name} 导入新金额 {subsidy_amount}，已重置补贴池数据")
                        pool = existing_pool  # 使用更新后的补贴池
                        should_generate_tasks = True  # 需要生成新任务
                else:
                    # 检查是否为0元补贴
                    if subsidy_amount == Decimal('0'):
                        # 新学生导入0元补贴：不创建补贴池，直接跳过后续处理
                        logger.info(f"新学生 {student_name} 导入0元补贴，跳过创建补贴池")
                        total_students += 1  # 只统计学生数量
                        continue
                    else:
                        # 创建新的补贴池（每日补贴）
                        pool = VirtualOrderPool(
                            student_id=student_info.roleId,
                            student_name=student_name,
                            total_subsidy=subsidy_amount,  # 每日补贴额度
                            remaining_amount=subsidy_amount,  # 初始剩余等于每日额度
                            allocated_amount=subsidy_amount,  # 已分配等于每日额度
                            completed_amount=Decimal('0'),  # 当日完成初始为0
                            status='active',
                            import_batch=import_batch,
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                            last_allocation_at=datetime.now()
                        )
                        self.db.add(pool)
                        should_generate_tasks = True  # 新学生需要生成任务

                # 只有需要生成任务且有有效补贴池才生成虚拟任务和统计
                if subsidy_amount > Decimal('0') and pool is not None and should_generate_tasks:
                    # 按需生成虚拟任务（只生成1-2个任务）
                    tasks = self.generate_on_demand_virtual_tasks_for_student(
                        student_info.roleId, student_name, subsidy_amount
                    )

                    # 保存任务到数据库
                    for task in tasks:
                        self.db.add(task)

                    # 更新补贴池：扣减已生成任务的金额
                    generated_amount = sum(task.commission for task in tasks)
                    pool.remaining_amount = subsidy_amount - generated_amount
                    pool.allocated_amount = subsidy_amount  # 已分配等于总补贴

                    logger.info(f"学生 {student_name} 按需生成了 {len(tasks)} 个任务，总金额: {generated_amount}，剩余: {pool.remaining_amount}")

                    total_students += 1
                    total_subsidy += subsidy_amount
                    total_generated_tasks += len(tasks)
                elif subsidy_amount > Decimal('0') and pool is not None and not should_generate_tasks:
                    # 相同金额重复导入：不生成新任务，但统计学生和补贴
                    total_students += 1
                    total_subsidy += subsidy_amount
                    logger.info(f"学生 {student_name} 重复导入相同金额，跳过任务生成")
                else:
                    # 0元补贴或无有效补贴池的情况，只统计学生数量
                    total_students += 1

            # 提交事务
            self.db.commit()

            return {
                'import_batch': import_batch,
                'total_students': total_students,
                'total_subsidy': float(total_subsidy),
                'generated_tasks': total_generated_tasks
            }

        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"导入学生补贴数据失败: {str(e)}",
                data=None
            )

    def import_customer_service_data(self, cs_data: List[Dict]) -> Dict[str, Any]:
        """
        导入专用客服数据

        Args:
            cs_data: 客服数据列表

        Returns:
            Dict: 导入结果统计
        """
        try:
            total_imported = 0
            failed_count = 0
            failed_details = []

            for data in cs_data:
                try:
                    name = data['name']
                    account = data['account']

                    # 检查账号是否已存在
                    existing_user = self.db.query(OriginalUser).filter(
                        OriginalUser.username == account,
                        OriginalUser.isDeleted == False
                    ).first()

                    if existing_user:
                        failed_count += 1
                        failed_details.append(f"账号 {account} 已存在")
                        continue

                    # 创建用户账号
                    user = OriginalUser(
                        username=account,
                        password='$2b$12$defaultpasswordhash',  # 默认密码，需要后续修改
                        role='6',  # 虚拟客服角色
                        lastLoginTime=None,
                        isDeleted=False
                    )
                    self.db.add(user)
                    self.db.flush()  # 获取用户ID

                    # 创建用户信息
                    user_info = UserInfo(
                        userId=user.id,
                        name=name,
                        account=account,
                        phone_number=data.get('phone_number'),
                        id_card=data.get('id_card'),
                        level='6',  # 虚拟订单专用客服级别
                        parentId=12,  # 归属于管理员账号
                        needsComputer='否',  # 虚拟客服不需要电脑
                        isDeleted=False
                    )
                    self.db.add(user_info)

                    total_imported += 1

                except Exception as e:
                    failed_count += 1
                    failed_details.append(f"导入 {data.get('name', '未知')} 失败: {str(e)}")

            # 提交事务
            self.db.commit()

            return {
                'total_imported': total_imported,
                'failed_count': failed_count,
                'failed_details': failed_details if failed_details else None
            }

        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"导入专用客服数据失败: {str(e)}",
                data=None
            )

    def get_virtual_order_stats(self) -> Dict[str, Any]:
        """获取虚拟订单统计信息"""
        try:
            # 统计学生数量（只统计未删除的记录）
            total_students = self.db.query(VirtualOrderPool).filter(VirtualOrderPool.is_deleted == False).count()

            # 统计总补贴金额（只统计未删除的记录）
            total_subsidy_result = self.db.query(func.sum(VirtualOrderPool.total_subsidy)).filter(VirtualOrderPool.is_deleted == False).scalar()
            total_subsidy = float(total_subsidy_result) if total_subsidy_result else 0.0

            # 统计生成的任务数量
            total_tasks_generated = self.db.query(Tasks).filter(Tasks.is_virtual.is_(True)).count()

            # 统计完成的任务数量 (status=4表示已完成)
            total_tasks_completed = self.db.query(Tasks).filter(
                and_(Tasks.is_virtual.is_(True), Tasks.status == '4')
            ).count()

            # 计算完成率
            completion_rate = (total_tasks_completed / total_tasks_generated * 100) if total_tasks_generated > 0 else 0.0

            return {
                'total_students': total_students,
                'total_subsidy': total_subsidy,
                'total_tasks_generated': total_tasks_generated,
                'total_tasks_completed': total_tasks_completed,
                'completion_rate': round(completion_rate, 2)
            }

        except Exception as e:
            raise BusinessException(
                code=500,
                message=f"获取虚拟订单统计失败: {str(e)}",
                data=None
            )

    def get_virtual_order_daily_stats(self, target_date: str = None) -> Dict[str, Any]:
        """获取虚拟订单当天统计信息

        Args:
            target_date: 目标日期 (YYYY-MM-DD)，为空则使用当天

        Returns:
            Dict: 当天统计信息
        """
        try:
            from datetime import datetime, date

            # 确定目标日期
            if target_date:
                target_date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
            else:
                target_date_obj = date.today()

            # 计算当天的开始和结束时间
            start_datetime = datetime.combine(target_date_obj, datetime.min.time())
            end_datetime = datetime.combine(target_date_obj, datetime.max.time())

            # 统计当天生成的虚拟任务数量
            daily_tasks_generated = self.db.query(Tasks).filter(
                and_(
                    Tasks.is_virtual.is_(True),
                    Tasks.created_at >= start_datetime,
                    Tasks.created_at <= end_datetime
                )
            ).count()

            # 统计当天完成的虚拟任务数量 (status=4表示已完成)
            daily_tasks_completed = self.db.query(Tasks).filter(
                and_(
                    Tasks.is_virtual.is_(True),
                    Tasks.status == '4',
                    Tasks.updated_at >= start_datetime,
                    Tasks.updated_at <= end_datetime
                )
            ).count()

            # 统计当天完成任务的补贴金额
            daily_subsidy_result = self.db.query(func.sum(Tasks.commission)).filter(
                and_(
                    Tasks.is_virtual.is_(True),
                    Tasks.status == '4',
                    Tasks.updated_at >= start_datetime,
                    Tasks.updated_at <= end_datetime
                )
            ).scalar()
            daily_subsidy = float(daily_subsidy_result) if daily_subsidy_result else 0.0

            # 统计当天有任务活动的学生人数（生成或完成任务的学生）
            # 当天生成任务的学生
            generated_students = self.db.query(Tasks.target_student_id).filter(
                and_(
                    Tasks.is_virtual.is_(True),
                    Tasks.target_student_id.isnot(None),
                    Tasks.created_at >= start_datetime,
                    Tasks.created_at <= end_datetime
                )
            ).distinct().all()

            # 当天完成任务的学生
            completed_students = self.db.query(Tasks.target_student_id).filter(
                and_(
                    Tasks.is_virtual.is_(True),
                    Tasks.status == '4',
                    Tasks.target_student_id.isnot(None),
                    Tasks.updated_at >= start_datetime,
                    Tasks.updated_at <= end_datetime
                )
            ).distinct().all()

            # 合并去重，统计当天活跃学生数
            active_student_ids = set()
            for student in generated_students:
                if student[0]:
                    active_student_ids.add(student[0])
            for student in completed_students:
                if student[0]:
                    active_student_ids.add(student[0])

            daily_active_students = len(active_student_ids)

            # 计算当天完成率
            daily_completion_rate = (daily_tasks_completed / daily_tasks_generated * 100) if daily_tasks_generated > 0 else 0.0

            return {
                'date': target_date_obj.isoformat(),
                'daily_tasks_generated': daily_tasks_generated,
                'daily_tasks_completed': daily_tasks_completed,
                'daily_subsidy': daily_subsidy,
                'daily_active_students': daily_active_students,
                'daily_completion_rate': round(daily_completion_rate, 2)
            }

        except Exception as e:
            raise BusinessException(
                code=500,
                message=f"获取虚拟订单当天统计失败: {str(e)}",
                data=None
            )

    def get_student_pools(self, page: int = 1, size: int = 20, status: str = None) -> Dict[str, Any]:
        """获取学生补贴池列表（包含奖金池信息）"""
        try:
            from shared.models.student_daily_achievement import StudentDailyAchievement
            from shared.models.bonus_pool import BonusPool

            query = self.db.query(VirtualOrderPool).filter(
                VirtualOrderPool.is_deleted == False
            )

            # 状态过滤
            if status:
                query = query.filter(VirtualOrderPool.status == status)

            # 总数统计
            total = query.count()

            # 分页查询
            offset = (page - 1) * size
            pools = query.offset(offset).limit(size).all()

            # 获取昨天的日期（用于判断达标）
            yesterday = date.today() - timedelta(days=1)

            # 转换为字典格式
            items = []
            for pool in pools:
                # 自动同步该学生的已完成任务金额
                self._sync_student_completed_amount(pool)

                # 检查学生昨天是否达标
                yesterday_achievement = self.db.query(StudentDailyAchievement).filter(
                    StudentDailyAchievement.student_id == pool.student_id,
                    StudentDailyAchievement.achievement_date == yesterday,
                    StudentDailyAchievement.is_achieved == True
                ).first()

                is_qualified = yesterday_achievement is not None

                # 计算完成率（基于实际获得金额）
                completion_rate = 0.0
                if pool.total_subsidy > 0:
                    completion_rate = float(pool.consumed_subsidy / pool.total_subsidy * 100)

                # 查询学员的代理返佣比例
                agent_rebate = None
                user_info = self.db.query(UserInfo).filter(UserInfo.roleId == pool.student_id).first()
                if user_info and user_info.agentId:
                    agent = self.db.query(Agents).filter(Agents.id == user_info.agentId).first()
                    if agent:
                        agent_rebate = agent.agent_rebate

                items.append({
                    'id': pool.id,
                    'student_id': pool.student_id,
                    'student_name': pool.student_name,
                    'total_subsidy': float(pool.total_subsidy),  # 每日补贴额度
                    'remaining_amount': float(pool.remaining_amount),  # 剩余金额（不再包含奖金池）
                    'allocated_amount': float(pool.allocated_amount),
                    'completed_amount': float(pool.completed_amount),  # 当日已完成
                    'consumed_subsidy': float(pool.consumed_subsidy),  # 当日实际消耗的补贴金额
                    'completion_rate': round(completion_rate, 2),  # 完成率
                    'is_qualified': is_qualified,  # 是否达标
                    'agent_rebate': agent_rebate,  # 代理返佣比例
                    'status': pool.status,
                    'import_batch': pool.import_batch,
                    'created_at': pool.created_at,
                    'last_allocation_at': pool.last_allocation_at
                })

            return {
                'items': items,
                'total': total,
                'page': page,
                'size': size
            }

        except Exception as e:
            raise BusinessException(
                code=500,
                message=f"获取学生补贴池列表失败: {str(e)}",
                data=None
            )



    def _sync_student_completed_amount(self, pool: VirtualOrderPool) -> None:
        """
        同步单个学生的当日已完成任务金额

        Args:
            pool: 学生补贴池对象
        """
        try:
            # 获取今天的日期范围
            today_start = datetime.combine(date.today(), datetime.min.time())
            today_end = datetime.combine(date.today(), datetime.max.time())

            # 查询该学生今天已完成的虚拟任务
            completed_tasks = self.db.query(Tasks).filter(
                and_(
                    Tasks.is_virtual.is_(True),
                    Tasks.target_student_id == pool.student_id,
                    Tasks.status == '4',  # 已完成状态
                    Tasks.created_at >= today_start,  # 今天创建的任务
                    Tasks.created_at <= today_end
                )
            ).all()

            # 计算今日实际已完成金额（任务面值）
            actual_completed_amount = sum(task.commission for task in completed_tasks)

            # 获取学生的返佣比例
            rebate_rate = self.get_student_rebate_rate(pool.student_id)

            # 计算实际消耗的补贴（面值 × 返佣比例）
            actual_consumed_subsidy = actual_completed_amount * rebate_rate

            # 更新补贴池
            if pool.completed_amount != actual_completed_amount or pool.consumed_subsidy != actual_consumed_subsidy:
                pool.completed_amount = actual_completed_amount
                pool.consumed_subsidy = actual_consumed_subsidy

                # 重新计算剩余金额（基于实际消耗的补贴）
                pool.remaining_amount = pool.total_subsidy - pool.consumed_subsidy
                # 已分配金额始终等于总补贴金额
                pool.allocated_amount = pool.total_subsidy

                # 确保剩余金额不为负数
                if pool.remaining_amount < 0:
                    pool.remaining_amount = Decimal('0')

                pool.updated_at = datetime.now()
                self.db.commit()

        except Exception as e:
            # 同步失败不影响主流程，只记录错误
            print(f"同步学生 {pool.student_id} 完成金额失败: {str(e)}")

    def reallocate_student_tasks(self, student_id: int) -> Dict[str, Any]:
        """重新分配学生任务"""
        try:
            # 获取学生补贴池
            pool = self.db.query(VirtualOrderPool).filter(
                VirtualOrderPool.student_id == student_id,
                VirtualOrderPool.is_deleted == False
            ).first()

            if not pool:
                raise BusinessException(
                    code=404,
                    message="未找到该学生的补贴池",
                    data=None
                )

            if pool.remaining_amount <= 0:
                raise BusinessException(
                    code=400,
                    message="该学生没有剩余金额可分配",
                    data=None
                )

            # 删除该学生未接取的虚拟任务
            self.db.query(Tasks).filter(
                and_(
                    Tasks.is_virtual.is_(True),
                    Tasks.target_student_id == student_id,
                    Tasks.status == '0'  # 修改为数字状态
                )
            ).delete()

            # 基于剩余补贴重新生成任务
            tasks = self.generate_virtual_tasks_for_student(
                student_id, pool.student_name, pool.remaining_amount
            )

            # 保存新任务
            for task in tasks:
                self.db.add(task)

            # 更新补贴池信息
            # 已分配金额始终等于总补贴金额（不需要更新）
            # pool.allocated_amount = pool.total_subsidy
            pool.last_allocation_at = datetime.now()
            pool.updated_at = datetime.now()

            self.db.commit()

            return {
                'student_id': student_id,
                'remaining_amount': float(pool.remaining_amount),
                'new_tasks_count': len(tasks)
            }

        except BusinessException:
            raise
        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"重新分配学生任务失败: {str(e)}",
                data=None
            )

    def reset_student_pool(self, student_id: int) -> Dict[str, Any]:
        """
        重置学生补贴池的完成状态，清空已完成金额和消耗补贴，重新生成任务

        Args:
            student_id: 学生ID

        Returns:
            Dict: 重置结果
        """
        try:
            # 获取学生补贴池
            pool = self.db.query(VirtualOrderPool).filter(
                VirtualOrderPool.student_id == student_id,
                VirtualOrderPool.is_deleted == False
            ).first()

            if not pool:
                raise BusinessException(
                    code=404,
                    message="未找到该学生的补贴池",
                    data=None
                )

            # 删除该学生所有未完成的虚拟任务
            deleted_tasks = self.db.query(Tasks).filter(
                and_(
                    Tasks.is_virtual.is_(True),
                    Tasks.target_student_id == student_id,
                    Tasks.status.in_(['0'])  # 只删除待接取的任务
                )
            ).all()

            for task in deleted_tasks:
                self.db.delete(task)

            # 重置补贴池状态
            original_completed = float(pool.completed_amount)
            original_consumed = float(pool.consumed_subsidy)

            pool.completed_amount = Decimal('0')  # 清空已完成金额
            pool.consumed_subsidy = Decimal('0')  # 清空消耗补贴
            pool.remaining_amount = pool.total_subsidy  # 重置剩余金额为总补贴
            pool.allocated_amount = pool.total_subsidy  # 已分配等于总补贴
            pool.updated_at = datetime.now()
            pool.last_allocation_at = datetime.now()

            # 使用虚拟客服分配策略重新生成任务
            result = self.generate_virtual_tasks_with_service_allocation(
                student_id, pool.student_name, pool.remaining_amount
            )

            self.db.commit()

            return {
                'student_id': student_id,
                'student_name': pool.student_name,
                'deleted_tasks_count': len(deleted_tasks),
                'original_completed_amount': original_completed,
                'original_consumed_subsidy': original_consumed,
                'reset_remaining_amount': float(pool.remaining_amount),
                'regenerate_result': result,
                'message': f'成功重置学生 {pool.student_name} 的补贴池，删除了 {len(deleted_tasks)} 个待接取任务'
            }

        except BusinessException:
            raise
        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"重置学生补贴池失败: {str(e)}",
                data=None
            )

    def create_virtual_customer_service(self, name: str, account: str, initial_password: str = "123456") -> Dict[str, Any]:
        """
        创建虚拟订单专用客服

        Args:
            name: 客服姓名
            account: 客服账号
            initial_password: 初始密码（默认123456）

        Returns:
            Dict: 创建结果
        """
        try:
            from shared.models.virtual_customer_service import VirtualCustomerService

            # 检查账号是否已存在（在user表中）
            existing_user = self.db.query(OriginalUser).filter(
                OriginalUser.username == account,
                OriginalUser.isDeleted == False
            ).first()

            if existing_user:
                raise BusinessException(
                    code=400,
                    message=f"账号 {account} 已存在",
                    data=None
                )

            # 检查虚拟客服账号是否已存在
            existing_cs = self.db.query(VirtualCustomerService).filter(
                VirtualCustomerService.account == account,
                VirtualCustomerService.is_deleted == False
            ).first()

            if existing_cs:
                raise BusinessException(
                    code=400,
                    message=f"虚拟客服账号 {account} 已存在",
                    data=None
                )

            # 对密码进行哈希处理
            import bcrypt
            salt = bcrypt.gensalt(rounds=10)
            hashed_password = bcrypt.hashpw(initial_password.encode('utf-8'), salt).decode('utf-8')

            # 创建用户账号
            user = OriginalUser(
                username=account,
                password=hashed_password,
                role='6',  # 虚拟客服角色设置为6
                lastLoginTime=None,
                isDeleted=False
            )
            self.db.add(user)
            self.db.flush()  # 获取用户ID

            # 创建虚拟客服记录 - initial_password也使用加密密码
            virtual_cs = VirtualCustomerService(
                user_id=user.id,
                name=name,
                account=account,
                initial_password=hashed_password,  # 存储加密后的密码，而不是明文
                level='6',
                status='active',
                is_deleted=False
            )
            self.db.add(virtual_cs)

            # 提交事务
            self.db.commit()

            return {
                'id': virtual_cs.id,
                'user_id': user.id,
                'name': name,
                'account': account,
                'level': '6',
                'status': 'active',
                'initial_password': initial_password  # 仍返回明文密码供前端显示，但数据库存储的是加密密码
            }

        except BusinessException:
            raise
        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"创建虚拟客服失败: {str(e)}",
                data=None
            )

    def get_student_available_tasks(self, student_id: int, include_bonus_pool: bool = True) -> List[Dict[str, Any]]:
        """
        获取学生可见的虚拟任务（包括普通虚拟任务和奖金池任务）

        Args:
            student_id: 学生ID
            include_bonus_pool: 是否包含奖金池任务

        Returns:
            List[Dict]: 可见任务列表
        """
        try:
            from datetime import date, timedelta
            from .bonus_pool_service import BonusPoolService

            tasks = []
            now = datetime.now()

            # 1. 获取专属虚拟任务（未过期且未接取）
            personal_tasks = self.db.query(Tasks).filter(
                Tasks.is_virtual == True,
                Tasks.is_bonus_pool == False,
                Tasks.target_student_id == student_id,
                Tasks.status == '0',  # 未接取
                Tasks.end_date > now  # 未过期
            ).all()

            for task in personal_tasks:
                tasks.append({
                    'id': task.id,
                    'type': 'personal',  # 个人专属任务
                    'summary': task.summary,
                    'requirement': task.requirement,
                    'commission': float(task.commission),
                    'order_number': task.order_number,
                    'end_date': task.end_date.isoformat() if task.end_date else None,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                    'task_level': task.task_level,
                    'source': task.source
                })

            # 2. 检查是否可以看到奖金池任务
            if include_bonus_pool:
                bonus_service = BonusPoolService(self.db)
                if bonus_service.check_student_bonus_access(student_id):
                    # 获取今日奖金池任务
                    today = date.today()
                    bonus_tasks = self.db.query(Tasks).filter(
                        Tasks.is_virtual == True,
                        Tasks.is_bonus_pool == True,
                        Tasks.bonus_pool_date == today,
                        Tasks.status == '0',  # 未接取
                        Tasks.end_date > now  # 未过期
                    ).all()

                    for task in bonus_tasks:
                        tasks.append({
                            'id': task.id,
                            'type': 'bonus_pool',  # 奖金池任务
                            'summary': task.summary,
                            'requirement': task.requirement,
                            'commission': float(task.commission),
                            'order_number': task.order_number,
                            'end_date': task.end_date.isoformat() if task.end_date else None,
                            'created_at': task.created_at.isoformat() if task.created_at else None,
                            'task_level': task.task_level,
                            'source': '奖金池'
                        })

            # 按创建时间倒序排序
            tasks.sort(key=lambda x: x['created_at'], reverse=True)

            return tasks

        except Exception as e:
            raise BusinessException(
                code=500,
                message=f"获取学生可见任务失败: {str(e)}",
                data=None
            )

    def accept_task(self, task_id: int, student_id: int) -> Dict[str, Any]:
        """
        学生接取任务

        Args:
            task_id: 任务ID
            student_id: 学生ID

        Returns:
            Dict: 接取结果
        """
        try:
            # 获取学生信息
            student = self.db.query(UserInfo).filter(
                UserInfo.roleId == student_id,
                UserInfo.level == '3',
                UserInfo.isDeleted == False
            ).first()

            if not student:
                raise BusinessException(code=404, msg="学生不存在")

            # 使用行锁防止并发接取
            task = self.db.query(Tasks).filter(
                Tasks.id == task_id,
                Tasks.status == '0'  # 未接取
            ).with_for_update().first()

            if not task:
                raise BusinessException(code=404, msg="任务不存在或已被接取")

            # 检查任务是否过期
            if task.end_date and task.end_date < datetime.now():
                raise BusinessException(code=400, msg="任务已过期")

            # 检查权限
            if task.is_bonus_pool:
                # 奖金池任务需要检查达标权限
                from .bonus_pool_service import BonusPoolService
                bonus_service = BonusPoolService(self.db)
                if not bonus_service.check_student_bonus_access(student_id):
                    raise BusinessException(code=403, msg="您没有权限接取奖金池任务，需要前一天达标")
            elif task.target_student_id and task.target_student_id != student_id:
                # 专属任务只能由指定学生接取
                raise BusinessException(code=403, msg="您没有权限接取此任务")

            # 更新任务状态
            task.status = '1'  # 已接取
            task.accepted_by = str(student_id)
            task.accepted_name = student.name
            task.order_received_number = 1
            task.updated_at = datetime.now()

            self.db.commit()

            return {
                'success': True,
                'task_id': task_id,
                'student_id': student_id,
                'student_name': student.name,
                'commission': float(task.commission),
                'delivery_date': task.delivery_date.isoformat() if task.delivery_date else None
            }

        except BusinessException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"接取任务失败: {str(e)}",
                data=None
            )

    def get_virtual_customer_services(self, page: int = 1, size: int = 20) -> Dict[str, Any]:
        """获取虚拟客服列表"""
        try:
            from shared.models.virtual_customer_service import VirtualCustomerService

            # 查询虚拟客服
            query = self.db.query(VirtualCustomerService).filter(
                VirtualCustomerService.is_deleted == False
            )

            # 总数统计
            total = query.count()

            # 分页查询
            offset = (page - 1) * size
            customer_services = query.offset(offset).limit(size).all()

            # 转换为字典格式
            items = []
            for cs in customer_services:
                # 获取关联的用户信息
                user = self.db.query(OriginalUser).filter(
                    OriginalUser.id == cs.user_id,
                    OriginalUser.isDeleted == False
                ).first()

                items.append({
                    'id': cs.id,
                    'user_id': cs.user_id,
                    'name': cs.name,
                    'account': cs.account,
                    'level': cs.level,
                    'status': cs.status,
                    'last_login_time': user.lastLoginTime if user else None,
                    'created_at': cs.created_at
                })

            return {
                'items': items,
                'total': total,
                'page': page,
                'size': size
            }

        except Exception as e:
            raise BusinessException(
                code=500,
                message=f"获取虚拟客服列表失败: {str(e)}",
                data=None
            )

    def update_virtual_customer_service(self, cs_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新虚拟客服信息"""
        try:
            from shared.models.virtual_customer_service import VirtualCustomerService

            # 查找虚拟客服
            cs = self.db.query(VirtualCustomerService).filter(
                VirtualCustomerService.id == cs_id,
                VirtualCustomerService.is_deleted == False
            ).first()

            if not cs:
                raise BusinessException(
                    code=404,
                    message="未找到该虚拟客服",
                    data=None
                )

            # 更新允许的字段
            allowed_fields = ['name', 'status']
            updated_fields = []

            for field in allowed_fields:
                if field in update_data and update_data[field] is not None:
                    setattr(cs, field, update_data[field])
                    updated_fields.append(field)

            # 处理密码更新
            if 'new_password' in update_data and update_data['new_password'] is not None:
                new_password = update_data['new_password'].strip()
                if new_password:  # 确保密码不为空
                    from shared.models.original_user import OriginalUser
                    import bcrypt

                    # 加密新密码
                    salt = bcrypt.gensalt(rounds=10)
                    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')

                    # 更新虚拟客服表的密码
                    cs.initial_password = hashed_password

                    # 同时更新关联的用户表密码
                    user = self.db.query(OriginalUser).filter(
                        OriginalUser.id == cs.user_id,
                        OriginalUser.isDeleted == False
                    ).first()

                    if user:
                        user.password = hashed_password
                        updated_fields.append('password')
                    else:
                        raise BusinessException(
                            code=404,
                            message="未找到对应的用户记录",
                            data=None
                        )

            if updated_fields:
                self.db.commit()

            return {
                'id': cs.id,
                'name': cs.name,
                'account': cs.account,
                'status': cs.status,
                'updated_fields': updated_fields
            }

        except BusinessException:
            raise
        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"更新虚拟客服失败: {str(e)}",
                data=None
            )

    def delete_virtual_customer_service(self, cs_id: int) -> Dict[str, Any]:
        """删除虚拟客服（软删除）"""
        try:
            from shared.models.virtual_customer_service import VirtualCustomerService

            # 查找虚拟客服
            cs = self.db.query(VirtualCustomerService).filter(
                VirtualCustomerService.id == cs_id,
                VirtualCustomerService.is_deleted == False
            ).first()

            if not cs:
                raise BusinessException(
                    code=404,
                    message="未找到该虚拟客服",
                    data=None
                )

            # 软删除虚拟客服记录
            # 修改account字段以避免唯一约束冲突
            deleted_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            cs.account = f"{cs.account}_deleted_{deleted_timestamp}"
            cs.is_deleted = True

            # 软删除关联的用户账号
            user = self.db.query(OriginalUser).filter(
                OriginalUser.id == cs.user_id
            ).first()

            if user:
                user.isDeleted = True

            self.db.commit()

            return {
                'id': cs.id,
                'name': cs.name,
                'account': cs.account,
                'deleted': True
            }

        except BusinessException:
            raise
        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"删除虚拟客服失败: {str(e)}",
                data=None
            )

    def delete_student_pool(self, pool_id: int) -> Dict[str, Any]:
        """删除学生补贴池（软删除），同步删除相关的未完成虚拟任务"""
        try:
            # 查找学生补贴池
            pool = self.db.query(VirtualOrderPool).filter(
                VirtualOrderPool.id == pool_id,
                VirtualOrderPool.is_deleted == False
            ).first()

            if not pool:
                raise BusinessException(
                    code=404,
                    message="未找到该学生补贴池记录",
                    data=None
                )

            # 查找该学生的未完成虚拟任务
            from shared.models.tasks import Tasks
            pending_tasks = self.db.query(Tasks).filter(
                Tasks.target_student_id == pool.student_id,
                Tasks.status.in_(['0', '1', '2']),  # 未接单、已接单、进行中
                Tasks.is_virtual == True  # 使用is_virtual字段更准确判断
            ).all()

            pending_tasks_count = len(pending_tasks)

            # 删除未完成的虚拟任务
            if pending_tasks:
                for task in pending_tasks:
                    # 先清理图片引用，避免外键约束错误
                    try:
                        from shared.models.resource_images import ResourceImages
                        # 将引用该任务的图片的used_in_task_id设为NULL
                        self.db.query(ResourceImages).filter(
                            ResourceImages.used_in_task_id == task.id
                        ).update({
                            'used_in_task_id': None,
                            'updated_at': datetime.now()
                        })
                        self.db.flush()  # 确保更新生效
                    except Exception as img_error:
                        logger.warning(f"清理任务 {task.id} 的图片引用失败: {str(img_error)}")

                    # 删除任务
                    self.db.delete(task)

            # 执行补贴池软删除
            pool.is_deleted = True
            pool.deleted_at = datetime.now()
            pool.status = 'deleted'

            self.db.commit()

            return {
                "id": pool.id,
                "student_id": pool.student_id,
                "student_name": pool.student_name,
                "total_subsidy": float(pool.total_subsidy),
                "remaining_amount": float(pool.remaining_amount),
                "deleted_pending_tasks": pending_tasks_count,  # 返回删除的任务数量
                "deleted": True,
                "deleted_at": pool.deleted_at.isoformat()
            }

        except BusinessException:
            raise
        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"删除学生补贴池失败: {str(e)}",
                data=None
            )

    def export_student_income_data(self, start_date: str = None, end_date: str = None,
                                 student_ids: List[int] = None) -> bytes:
        """
        导出学生收入数据为Excel

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            student_ids: 指定学生ID列表

        Returns:
            bytes: Excel文件内容
        """
        try:
            from sqlalchemy import and_, func
            from sqlalchemy.sql import case
            from shared.models.tasks import Tasks
            from shared.models.userinfo import UserInfo
            from shared.models.original_user import OriginalUser
            import pandas as pd
            import io

            # 查询所有学生
            students_query = self.db.query(UserInfo).filter(
                UserInfo.level == '3',  # 学员级别
                UserInfo.isDeleted == False
            )

            # 添加学生ID过滤
            if student_ids:
                students_query = students_query.filter(UserInfo.roleId.in_(student_ids))

            students = students_query.all()

            # 创建结果列表
            results = []
            for student in students:
                # 查询该学生的任务统计（只查询真实任务，不包括虚拟任务）
                task_conditions = [
                    Tasks.is_virtual.is_(False),  # 只查询真实任务
                    Tasks.accepted_by.like(f'%{student.roleId}%')  # 该学生接取的任务
                ]

                # 添加日期过滤
                if start_date:
                    start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                    task_conditions.append(Tasks.created_at >= start_datetime)
                if end_date:
                    end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                    task_conditions.append(Tasks.created_at <= end_datetime)

                # 统计该学生的任务数据
                task_stats = self.db.query(
                    func.count(Tasks.id).label('total_tasks'),
                    func.sum(Tasks.commission).label('total_income'),
                    func.count(
                        case((Tasks.status == '已完成', 1))
                    ).label('completed_tasks'),
                    func.sum(
                        case((Tasks.status == '已完成', Tasks.commission), else_=0)
                    ).label('completed_income')
                ).filter(and_(*task_conditions)).first()

                # 为每个学生创建一个记录
                class StudentResult:
                    def __init__(self, student_id, student_name, phone_number, id_card,
                               total_tasks, total_income, completed_tasks, completed_income):
                        self.student_id = student_id
                        self.student_name = student_name
                        self.phone_number = phone_number
                        self.id_card = id_card
                        self.total_tasks = total_tasks
                        self.total_income = total_income
                        self.completed_tasks = completed_tasks
                        self.completed_income = completed_income

                result = StudentResult(
                    student_id=student.roleId,
                    student_name=student.name or '',
                    phone_number=student.phone_number or '',
                    id_card='',  # 不显示身份证
                    total_tasks=task_stats.total_tasks or 0,
                    total_income=float(task_stats.total_income or 0),
                    completed_tasks=task_stats.completed_tasks or 0,
                    completed_income=float(task_stats.completed_income or 0)
                )
                results.append(result)

            # 转换为DataFrame
            data = []
            for row in results:
                data.append({
                    '学生ID': row.student_id,
                    '学生姓名': row.student_name or '',
                    '手机号': row.phone_number or '',
                    '总任务数': row.total_tasks or 0,
                    '总收入金额': float(row.total_income or 0),
                    '已完成任务数': row.completed_tasks or 0,
                    '已完成收入': float(row.completed_income or 0),
                    '完成率': round((row.completed_tasks or 0) / max(row.total_tasks or 1, 1) * 100, 2),
                    '导出时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    '补贴金额': 0  # 这一列供用户填写补贴金额
                })

            if not data:
                # 如果没有数据，创建一个示例行
                data.append({
                    '学生ID': '',
                    '学生姓名': '示例学生',
                    '手机号': '',
                    '总任务数': 0,
                    '总收入金额': 0.0,
                    '已完成任务数': 0,
                    '已完成收入': 0.0,
                    '完成率': 0.0,
                    '导出时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    '补贴金额': 200.0  # 示例补贴金额
                })

            df = pd.DataFrame(data)

            # 创建Excel文件
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # 写入学生收入数据
                df.to_excel(writer, sheet_name='学生收入统计', index=False)

                # 获取工作表对象进行格式化
                worksheet = writer.sheets['学生收入统计']

                # 设置列宽
                column_widths = {
                    'A': 10,  # 学生ID
                    'B': 15,  # 学生姓名
                    'C': 15,  # 手机号
                    'D': 20,  # 身份证号
                    'E': 12,  # 总任务数
                    'F': 15,  # 总收入金额
                    'G': 15,  # 已完成任务数
                    'H': 15,  # 已完成收入
                    'I': 10,  # 完成率
                    'J': 20,  # 导出时间
                    'K': 15,  # 补贴金额
                }

                for col, width in column_widths.items():
                    worksheet.column_dimensions[col].width = width

                # 添加说明工作表
                instructions = pd.DataFrame([
                    ['说明', ''],
                    ['1. 学生收入统计', '显示学生的任务完成情况和收入统计'],
                    ['2. 补贴金额列', '请在此列填写要给学生的补贴金额'],
                    ['3. 导入流程', '填写补贴金额后，将此文件导入到虚拟订单系统'],
                    ['4. 注意事项', '补贴金额必须为正数，系统会自动生成5的倍数任务'],
                    ['', ''],
                    ['字段说明', ''],
                    ['学生ID', '系统内部学生唯一标识'],
                    ['学生姓名', '学生真实姓名'],
                    ['手机号', '学生联系电话'],
                    ['身份证号', '学生身份证号码'],
                    ['总任务数', '学生接取的所有任务数量'],
                    ['总收入金额', '学生所有任务的总金额'],
                    ['已完成任务数', '学生已完成的任务数量'],
                    ['已完成收入', '学生已完成任务的收入金额'],
                    ['完成率', '任务完成率百分比'],
                    ['导出时间', '数据导出的时间'],
                    ['补贴金额', '要给学生的补贴金额（请填写）']
                ], columns=['项目', '说明'])

                instructions.to_excel(writer, sheet_name='使用说明', index=False)

                # 设置说明工作表的列宽
                instructions_sheet = writer.sheets['使用说明']
                instructions_sheet.column_dimensions['A'].width = 20
                instructions_sheet.column_dimensions['B'].width = 50

            output.seek(0)
            return output.getvalue()

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"导出学生收入数据失败的详细错误: {error_details}")
            raise BusinessException(
                code=500,
                message=f"导出学生收入数据失败: {str(e)}",
                data=None
            )

    def get_student_income_summary(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        获取学生收入汇总统计

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            Dict: 汇总统计数据
        """
        try:
            from sqlalchemy import and_, func
            from sqlalchemy.sql import case
            from shared.models.tasks import Tasks
            from shared.models.userinfo import UserInfo
            from shared.models.virtual_order_pool import VirtualOrderPool

            # 基础查询 - 统计学生数量
            query = self.db.query(UserInfo).filter(
                UserInfo.level == '3',  # 学员级别
                UserInfo.isDeleted == False
            )

            total_students = query.count()

            # 从补贴池统计总补贴金额（只统计未删除的记录）
            pool_stats = self.db.query(
                func.sum(VirtualOrderPool.total_subsidy).label('total_subsidy'),
                func.sum(VirtualOrderPool.completed_amount).label('total_completed')
            ).filter(VirtualOrderPool.is_deleted == False).first()

            # 任务统计查询 (status=4表示已完成)
            task_query = self.db.query(
                func.count(Tasks.id).label('total_tasks'),
                func.count(
                    case((Tasks.status == '4', 1))
                ).label('completed_tasks')
            ).filter(Tasks.is_virtual.is_(True))  # 只统计虚拟任务

            # 添加日期过滤
            if start_date:
                task_query = task_query.filter(Tasks.created_at >= start_date)
            if end_date:
                task_query = task_query.filter(Tasks.created_at <= end_date)

            task_stats = task_query.first()

            # 使用补贴池的数据作为总金额和已完成金额
            total_amount = float(pool_stats.total_subsidy or 0)
            completed_amount = float(pool_stats.total_completed or 0)

            return {
                'total_students': total_students,
                'total_tasks': task_stats.total_tasks or 0,
                'total_amount': total_amount,  # 使用补贴池的总补贴金额
                'completed_tasks': task_stats.completed_tasks or 0,
                'completed_amount': completed_amount,  # 使用补贴池的已完成金额
                'completion_rate': round(
                    (task_stats.completed_tasks or 0) / max(task_stats.total_tasks or 1, 1) * 100, 2
                ),
                'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        except Exception as e:
            raise BusinessException(
                code=500,
                message=f"获取学生收入汇总失败: {str(e)}",
                data=None
            )



    def get_student_income_stats(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        获取学生收入统计信息

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            Dict: 统计信息
        """
        try:
            from sqlalchemy import and_, func
            from shared.models.tasks import Tasks

            # 构建查询条件
            query_conditions = [
                Tasks.is_virtual.is_(False),  # 只查询真实任务
                Tasks.status == '已完成',   # 只查询已完成的任务
                Tasks.accepted_by.isnot(None)  # 有接取人的任务
            ]

            # 添加日期过滤
            if start_date:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                query_conditions.append(Tasks.created_at >= start_datetime)

            if end_date:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                query_conditions.append(Tasks.created_at <= end_datetime)

            # 统计查询
            total_tasks = self.db.query(Tasks).filter(and_(*query_conditions)).count()
            total_income = self.db.query(func.sum(Tasks.commission)).filter(and_(*query_conditions)).scalar() or 0

            # 统计学生数量（去重）
            student_count_query = self.db.query(Tasks.accepted_by).filter(and_(*query_conditions)).distinct()
            unique_students = set()
            for result in student_count_query:
                if result.accepted_by:
                    try:
                        student_id = int(result.accepted_by.split(',')[0]) if ',' in result.accepted_by else int(result.accepted_by)
                        unique_students.add(student_id)
                    except (ValueError, AttributeError):
                        continue

            return {
                'total_students': len(unique_students),
                'total_tasks': total_tasks,
                'total_income': float(total_income),
                'average_income_per_student': round(float(total_income) / len(unique_students), 2) if unique_students else 0,
                'average_income_per_task': round(float(total_income) / total_tasks, 2) if total_tasks > 0 else 0,
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                }
            }

        except Exception as e:
            raise BusinessException(
                code=500,
                message=f"获取学生收入统计失败: {str(e)}",
                data=None
            )

    def update_virtual_task_completion(self, task_id: int) -> Dict[str, Any]:
        """
        更新虚拟任务完成状态，同时更新学生补贴池的完成金额

        Args:
            task_id: 任务ID

        Returns:
            Dict: 更新结果
        """
        try:
            # 查找虚拟任务
            task = self.db.query(Tasks).filter(
                and_(
                    Tasks.id == task_id,
                    Tasks.is_virtual.is_(True)
                )
            ).first()

            if not task:
                raise BusinessException(
                    code=404,
                    message="未找到指定的虚拟任务",
                    data=None
                )

            # 检查任务状态是否可以完成（排除已完成和终止状态）
            if task.status in ['4', '5']:
                raise BusinessException(
                    code=400,
                    message=f"任务状态为{task.status}，无法重复完成",
                    data=None
                )

            # 更新任务状态为已完成
            task.status = '4'
            task.payment_status = '4'
            task.value_recycled = True  # 标记价值已回收，避免重复处理
            task.updated_at = datetime.now()

            # 查找对应的学生补贴池
            pool = self.db.query(VirtualOrderPool).filter(
                VirtualOrderPool.student_id == task.target_student_id,
                VirtualOrderPool.is_deleted == False
            ).first()

            if not pool:
                raise BusinessException(
                    code=404,
                    message="未找到对应的学生补贴池",
                    data=None
                )

            # 获取学生的返佣比例
            rebate_rate = self.get_student_rebate_rate(task.target_student_id)

            # 更新补贴池的完成金额（任务面值）
            pool.completed_amount += task.commission

            # 更新实际消耗的补贴（面值 × 返佣比例）
            consumed_subsidy_for_this_task = task.commission * rebate_rate
            pool.consumed_subsidy += consumed_subsidy_for_this_task

            # 更新剩余金额：总补贴 - 实际消耗的补贴
            pool.remaining_amount = pool.total_subsidy - pool.consumed_subsidy

            # 已分配金额始终等于总补贴金额
            pool.allocated_amount = pool.total_subsidy

            # 确保剩余金额不为负数
            if pool.remaining_amount < 0:
                pool.remaining_amount = Decimal('0')

            pool.updated_at = datetime.now()

            # 计算剩余任务价值并重新生成任务
            student_actual_income = task.commission * rebate_rate  # 学生实际收入
            remaining_task_value = task.commission - student_actual_income  # 剩余价值

            logger.info(f"任务完成分析: 任务面值={task.commission}, 返佣比例={rebate_rate}, "
                       f"学生收入={student_actual_income}, 剩余价值={remaining_task_value}")

            generated_tasks_info = []

            # 如果有剩余价值，先加回补贴池，然后基于补贴池剩余金额重新生成任务
            if remaining_task_value > Decimal('0'):
                # 关键修复：把剩余价值加回补贴池
                pool.remaining_amount += remaining_task_value
                logger.info(f"剩余价值 {remaining_task_value} 已加回补贴池，当前剩余: {pool.remaining_amount}")

                # 基于补贴池剩余金额决定是否生成新任务
                if pool.remaining_amount > Decimal('0'):
                    try:
                        # 使用补贴池剩余金额生成任务，而不是直接使用剩余价值
                        allocation_result = self.allocator.allocate_tasks_to_services(
                            pool.remaining_amount, task.target_student_id, pool.student_name, on_demand=True
                        )

                        if allocation_result.success:
                            # 记录生成的任务信息
                            generated_amount = Decimal('0')
                            for allocated_task in allocation_result.allocated_tasks:
                                generated_tasks_info.append({
                                    'task_id': allocated_task['id'],
                                    'amount': allocated_task['amount'],
                                    'founder_id': allocated_task['founder_id'],
                                    'founder': allocated_task['founder']
                                })
                                generated_amount += Decimal(str(allocated_task['amount']))
                                logger.info(f"重新生成任务: ID={allocated_task['id']}, 金额={allocated_task['amount']}, "
                                           f"分配给客服: {allocated_task['founder']}")

                            # 更新补贴池剩余金额：扣减已生成的任务金额
                            pool.remaining_amount -= generated_amount
                            if pool.remaining_amount < 0:
                                pool.remaining_amount = Decimal('0')
                            logger.info(f"已生成任务总金额: {generated_amount}, 补贴池剩余: {pool.remaining_amount}")
                        else:
                            logger.warning(f"使用虚拟客服分配策略重新生成任务失败: {allocation_result.error_message}")
                            # 回退到原有方式（按需生成1-2个任务）
                            new_task_amounts = self.calculate_on_demand_task_amounts(pool.remaining_amount)
                            logger.info(f"回退到原有方式，补贴池剩余 {pool.remaining_amount} 分配为: {new_task_amounts}")

                            generated_amount = Decimal('0')
                            for amount in new_task_amounts:
                                new_task = self.create_virtual_task(task.target_student_id, pool.student_name, amount)
                                if new_task:
                                    self.db.add(new_task)
                                    generated_tasks_info.append({
                                        'task_id': new_task.id,
                                        'amount': float(amount),
                                        'founder_id': 0,
                                        'founder': '虚拟订单系统'
                                    })
                                    generated_amount += amount
                                    logger.info(f"回退方式生成任务: ID={new_task.id}, 金额={amount}")
                                else:
                                    logger.warning(f"图片资源不足，无法生成 {amount} 元的任务，停止生成")
                                    break

                            # 更新补贴池剩余金额
                            pool.remaining_amount -= generated_amount
                            if pool.remaining_amount < 0:
                                pool.remaining_amount = Decimal('0')
                            logger.info(f"回退方式生成任务总金额: {generated_amount}, 补贴池剩余: {pool.remaining_amount}")

                    except Exception as e:
                        logger.error(f"重新生成任务失败: {str(e)}")
                        # 不影响主流程，继续执行

            self.db.commit()

            return {
                'task_id': task_id,
                'student_id': task.target_student_id,
                'student_name': pool.student_name,
                'task_commission': float(task.commission),
                'student_actual_income': float(student_actual_income),
                'remaining_task_value': float(remaining_task_value),
                'generated_tasks': generated_tasks_info,
                'total_completed_amount': float(pool.completed_amount),
                'updated_at': pool.updated_at
            }

        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"更新虚拟任务完成状态失败: {str(e)}",
                data=None
            )

    def sync_completed_virtual_tasks(self) -> Dict[str, Any]:
        """
        同步所有已完成的虚拟任务到学生补贴池
        用于修复历史数据或手动同步

        Returns:
            Dict: 同步结果统计
        """
        try:
            # 查找所有已完成但未同步的虚拟任务
            completed_tasks = self.db.query(Tasks).filter(
                and_(
                    Tasks.is_virtual.is_(True),
                    Tasks.status == '4',
                    Tasks.target_student_id.isnot(None)
                )
            ).all()

            if not completed_tasks:
                return {
                    'synced_tasks': 0,
                    'affected_students': 0,
                    'total_amount': 0.0,
                    'message': '没有需要同步的已完成虚拟任务'
                }

            # 按学生分组统计
            student_tasks = {}
            for task in completed_tasks:
                student_id = task.target_student_id
                if student_id not in student_tasks:
                    student_tasks[student_id] = []
                student_tasks[student_id].append(task)

            synced_count = 0
            total_amount = Decimal('0')
            affected_students = 0

            for student_id, tasks in student_tasks.items():
                # 获取学生补贴池
                pool = self.db.query(VirtualOrderPool).filter(
                    VirtualOrderPool.student_id == student_id,
                    VirtualOrderPool.is_deleted == False
                ).first()

                if not pool:
                    continue

                # 计算该学生已完成任务的总金额
                student_completed_amount = sum(task.commission for task in tasks)

                # 重置并更新完成金额（避免重复计算）
                pool.completed_amount = student_completed_amount

                # 更新剩余金额：总补贴 - 已完成金额
                pool.remaining_amount = pool.total_subsidy - pool.completed_amount

                # 已分配金额始终等于总补贴金额
                pool.allocated_amount = pool.total_subsidy

                # 确保剩余金额不为负数
                if pool.remaining_amount < 0:
                    pool.remaining_amount = Decimal('0')

                pool.updated_at = datetime.now()

                synced_count += len(tasks)
                total_amount += student_completed_amount
                affected_students += 1

            self.db.commit()

            return {
                'synced_tasks': synced_count,
                'affected_students': affected_students,
                'total_amount': float(total_amount),
                'message': f'成功同步 {synced_count} 个已完成任务，影响 {affected_students} 个学生'
            }

        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"同步已完成虚拟任务失败: {str(e)}",
                data=None
            )

    def _get_reference_image_for_task(self, task_content: Dict[str, str]) -> Optional[str]:
        """
        根据任务内容获取合适的参考图片（优化版本，包含可用性检查）

        Args:
            task_content: 任务内容字典，包含summary、requirement和task_type

        Returns:
            Optional[str]: 图片URL，如果没有合适的图片则返回None
        """
        try:
            # 根据任务内容判断需要的图片类型
            category_code = self._determine_image_category(task_content)

            if not category_code:
                logger.warning("无法确定任务类型，跳过图片分配")
                return None

            # 检查是否需要使用资源库
            if not self._should_use_resource_library():
                logger.info("当前不使用资源库图片")
                return None

            # 调用资源库服务获取可用图片
            from services.resource_service.service.resource_service import ResourceService
            resource_service = ResourceService(self.db)

            # 直接尝试获取可用图片，ResourceService内部会处理是否有可用图片的逻辑

            # 先检查是否有可用图片
            image_result = resource_service.get_available_image_for_task(category_code)

            if not image_result.success or not image_result.image_id:
                logger.warning(f"分类 {category_code} 没有可用图片，无法生成任务")
                return None

            logger.info(f"为任务选择了图片: {image_result.image_code} (分类: {category_code})")
            return {
                'file_url': image_result.file_url,
                'image_id': image_result.image_id,
                'category_code': category_code,
                'original_filename': image_result.original_filename
            }

        except Exception as e:
            logger.error(f"获取参考图片失败: {str(e)}")
            return None

    def _should_use_resource_library(self) -> bool:
        """
        判断是否应该使用资源库图片

        Returns:
            bool: 是否使用资源库
        """
        try:
            # 100%使用资源库图片
            return True

        except Exception as e:
            logger.error(f"检查资源库使用策略失败: {str(e)}")
            return False

    def test_task_type_distribution(self, sample_size: int = 1000) -> Dict[str, Any]:
        """
        测试任务类型分布是否符合60:20:20比例

        Args:
            sample_size: 测试样本数量

        Returns:
            Dict: 测试结果统计
        """
        type_counts = {task_type: 0 for task_type in self.TASK_TYPE_WEIGHTS.keys()}

        # 生成测试样本
        for _ in range(sample_size):
            task_type = self._select_task_type_by_weight()
            type_counts[task_type] += 1

        # 计算实际比例
        actual_percentages = {}
        for task_type, count in type_counts.items():
            percentage = (count / sample_size) * 100
            actual_percentages[task_type] = round(percentage, 2)

        # 计算与期望比例的偏差
        expected_percentages = self.TASK_TYPE_WEIGHTS
        deviations = {}
        for task_type in type_counts.keys():
            deviation = abs(actual_percentages[task_type] - expected_percentages[task_type])
            deviations[task_type] = round(deviation, 2)

        return {
            'sample_size': sample_size,
            'expected_percentages': expected_percentages,
            'actual_percentages': actual_percentages,
            'actual_counts': type_counts,
            'deviations': deviations,
            'max_deviation': max(deviations.values()),
            'is_within_tolerance': max(deviations.values()) <= 5.0,  # 5%的容忍度
            'test_passed': max(deviations.values()) <= 5.0
        }

    def _determine_image_category(self, task_content) -> Optional[str]:
        """
        根据任务内容确定需要的图片分类

        Args:
            task_content: 任务内容字典或字符串

        Returns:
            Optional[str]: 分类代码
        """
        # 处理字典类型输入
        if isinstance(task_content, dict):
            task_type = task_content.get('task_type')
            if task_type and task_type in self.TASK_TYPE_WEIGHTS:
                return task_type
            # 兜底逻辑：如果没有任务类型，使用关键词匹配
            summary = task_content.get('summary', '').lower()
            requirement = task_content.get('requirement', '').lower()
        else:
            # 处理字符串类型输入
            summary = str(task_content).lower()
            requirement = ''

        # 关键词映射到分类
        category_keywords = {
            'avatar_redesign': [
                '头像', '人物', '肖像', '面部', '角色设计', '虚拟人物',
                'avatar', 'portrait', 'character', 'face'
            ],
            'room_decoration': [
                '装修', '房间', '室内', '家居', '设计', '空间', '毛坯房',
                'room', 'interior', 'decoration', 'design', 'home'
            ],
            'photo_extension': [
                '扩图', '全身', '半身', '扩展', '完整', 'extension',
                'full body', 'expand', 'complete'
            ]
        }

        # 评分每个分类
        category_scores = {}
        for category_code, keywords in category_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in summary:
                    score += 2  # summary中的关键词权重更高
                if keyword in requirement:
                    score += 1
            category_scores[category_code] = score

        # 选择得分最高的分类
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])
            if best_category[1] > 0:  # 至少有一个关键词匹配
                return best_category[0]

        # 如果没有明确匹配，默认返回头像改版
        return 'avatar_redesign'

    def mark_task_image_as_used(self, task_id: int) -> bool:
        """
        任务完成后标记使用的图片为已使用状态

        Args:
            task_id: 任务ID

        Returns:
            bool: 标记是否成功
        """
        try:
            # 查询任务信息
            task = self.db.query(Tasks).filter(Tasks.id == task_id).first()
            if not task or not task.reference_images:
                return False

            # 从reference_images中提取图片ID（如果存储了的话）
            # 这里需要根据实际的存储格式来解析
            # 由于当前存储的是URL，我们需要通过URL反查图片

            from services.resource_service.service.resource_service import ResourceService
            resource_service = ResourceService(self.db)

            # 通过URL查找图片并标记为已使用
            from shared.models.resource_images import ResourceImages, UsageStatus

            image = self.db.query(ResourceImages).filter(
                ResourceImages.file_url == task.reference_images,
                ResourceImages.usage_status == UsageStatus.available,
                ResourceImages.is_deleted == False
            ).first()

            if image:
                result = resource_service.mark_image_as_used(image.id, task_id)
                logger.info(f"任务 {task_id} 的图片 {image.id} 已标记为使用")
                return True

            return False

        except Exception as e:
            logger.error(f"标记任务图片为已使用失败: {str(e)}")
            return False

    def get_resource_library_stats(self) -> Dict[str, Any]:
        """
        获取资源库使用统计（用于虚拟任务系统报表）

        Returns:
            Dict: 资源库统计信息
        """
        try:
            from services.resource_service.service.resource_service import ResourceService
            resource_service = ResourceService(self.db)

            stats = resource_service.get_resource_stats()

            return {
                'total_images': stats.total_images,
                'available_images': stats.available_images,
                'used_images': stats.used_images,
                'usage_rate': round((stats.used_images / max(stats.total_images, 1)) * 100, 2),
                'categories_stats': stats.categories_stats
            }

        except Exception as e:
            logger.error(f"获取资源库统计失败: {str(e)}")
            return {
                'total_images': 0,
                'available_images': 0,
                'used_images': 0,
                'usage_rate': 0.0,
                'categories_stats': []
            }

    # ================ 新增：基于虚拟客服的任务分配方法 ================

    def generate_virtual_tasks_with_service_allocation(self,
                                                     student_id: int,
                                                     student_name: str,
                                                     subsidy_amount: Decimal,
                                                     on_demand: bool = False) -> Dict[str, Any]:
        """
        使用新的虚拟客服分配策略生成虚拟任务

        Args:
            student_id: 学生ID
            student_name: 学生姓名
            subsidy_amount: 可用补贴金额

        Returns:
            Dict: 生成结果
        """
        try:
            # 新逻辑：直接按补贴金额生成任务，不再除以返佣比例
            # 任务面值 = 补贴金额
            total_face_value = subsidy_amount

            # 使用新的分配策略
            allocation_result = self.allocator.allocate_tasks_to_services(
                total_face_value, student_id, student_name, on_demand
            )

            if allocation_result.success:
                return {
                    'success': True,
                    'message': f'成功为学生 {student_name} 分配 {len(allocation_result.allocated_tasks)} 个任务',
                    'tasks': allocation_result.allocated_tasks,
                    'total_amount': float(allocation_result.total_amount),
                    'subsidy_amount': float(subsidy_amount)
                }
            else:
                return {
                    'success': False,
                    'message': allocation_result.error_message or '任务分配失败',
                    'tasks': [],
                    'total_amount': 0.0
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'生成虚拟任务失败: {str(e)}',
                'tasks': [],
                'total_amount': 0.0
            }

    def import_student_subsidy_data_with_service_allocation(self,
                                                          student_data: List[Dict],
                                                          import_batch: str,
                                                          use_service_allocation: bool = True,
                                                          generate_tasks: bool = True) -> Dict[str, Any]:
        """
        导入学生每日补贴数据并使用虚拟客服分配策略生成任务

        Args:
            student_data: 学生数据列表
            import_batch: 导入批次号
            use_service_allocation: 是否使用虚拟客服分配策略
            generate_tasks: 是否生成虚拟任务（根据配置决定）

        Returns:
            Dict: 导入结果统计
        """
        try:
            total_students = 0
            total_subsidy = Decimal('0')
            total_generated_tasks = 0
            allocation_requests = []  # 用于批量分配

            # 第一阶段：更新补贴池数据
            for data in student_data:
                student_name = data['student_name']
                subsidy_amount = data['subsidy_amount']

                # 查找学生ID
                student_info = self.db.query(UserInfo).filter(
                    UserInfo.name == student_name,
                    UserInfo.level == '3',  # 学生级别
                    UserInfo.isDeleted == False
                ).first()

                if not student_info:
                    continue

                # 检查是否已存在该学生的补贴池（只查询未删除的记录）
                existing_pool = self.db.query(VirtualOrderPool).filter(
                    VirtualOrderPool.student_id == student_info.roleId,
                    VirtualOrderPool.is_deleted == False
                ).first()

                # 初始化任务生成标记
                should_generate_tasks = True

                if existing_pool:
                    # 检查是否为0元补贴（用于删除学生）
                    if subsidy_amount == Decimal('0'):
                        # 0元补贴：执行硬删除，彻底清理该学生的补贴池
                        self.db.delete(existing_pool)
                        logger.info(f"学生 {student_name} 导入0元补贴，已执行硬删除")
                        should_generate_tasks = False
                    elif existing_pool.total_subsidy == subsidy_amount:
                        # 相同金额：只更新导入批次，保持数据完整性，不清理任务，不生成新任务
                        existing_pool.import_batch = import_batch
                        existing_pool.updated_at = datetime.now()
                        logger.info(f"学生 {student_name} 重复导入相同金额 {subsidy_amount}，仅更新导入批次，保持数据完整性")
                        should_generate_tasks = False
                    else:
                        # 不同金额：清理旧任务，更新现有补贴池（以最新补贴金额为准，重置数据）
                        # 清理该学生之前的未完成虚拟任务（避免重复任务）
                        pending_tasks = self.db.query(Tasks).filter(
                            and_(
                                Tasks.is_virtual.is_(True),
                                Tasks.target_student_id == student_info.roleId,
                                Tasks.status.in_(['0'])  # 只删除待接取的任务
                            )
                        ).all()

                        for task in pending_tasks:
                            # 清理图片引用，避免外键约束错误
                            try:
                                from shared.models.resource_images import ResourceImages
                                self.db.query(ResourceImages).filter(
                                    ResourceImages.used_in_task_id == task.id
                                ).update({
                                    'used_in_task_id': None,
                                    'updated_at': datetime.now()
                                })
                                self.db.flush()
                            except Exception as img_error:
                                logger.warning(f"清理任务 {task.id} 的图片引用失败: {str(img_error)}")

                            self.db.delete(task)

                        existing_pool.total_subsidy = subsidy_amount  # 使用最新的补贴金额
                        existing_pool.remaining_amount = subsidy_amount  # 重置剩余金额为最新补贴金额
                        existing_pool.allocated_amount = subsidy_amount  # 重置已分配金额为最新补贴金额
                        existing_pool.completed_amount = Decimal('0')  # 重置已完成金额
                        existing_pool.consumed_subsidy = Decimal('0')  # 重置实际消耗补贴
                        existing_pool.import_batch = import_batch
                        existing_pool.updated_at = datetime.now()
                        existing_pool.last_allocation_at = datetime.now()
                        logger.info(f"学生 {student_name} 导入新金额 {subsidy_amount}，已重置补贴池数据")
                        should_generate_tasks = True
                else:
                    # 检查是否为0元补贴
                    if subsidy_amount == Decimal('0'):
                        # 新学生导入0元补贴：不创建补贴池，直接跳过
                        logger.info(f"新学生 {student_name} 导入0元补贴，跳过创建补贴池")
                        should_generate_tasks = False
                        total_students += 1  # 只统计学生数量
                        continue
                    else:
                        # 创建新的补贴池
                        pool = VirtualOrderPool(
                            student_id=student_info.roleId,
                            student_name=student_name,
                            total_subsidy=subsidy_amount,
                            remaining_amount=subsidy_amount,
                            allocated_amount=subsidy_amount,
                            completed_amount=Decimal('0'),
                            status='active',
                            import_batch=import_batch,
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                            last_allocation_at=datetime.now()
                        )
                        self.db.add(pool)
                        should_generate_tasks = True

                # 准备分配请求（只有需要生成任务时才添加）
                if use_service_allocation and should_generate_tasks and subsidy_amount > Decimal('0'):
                    allocation_requests.append({
                        'total_amount': subsidy_amount,
                        'student_id': student_info.roleId,
                        'student_name': student_name,
                        'on_demand': True  # 标记为按需生成
                    })

                total_students += 1
                if subsidy_amount > Decimal('0'):
                    total_subsidy += subsidy_amount

            # 提交补贴池更新
            self.db.commit()

            # 第二阶段：生成任务（根据配置决定是否生成）
            if generate_tasks and allocation_requests:
                if use_service_allocation:
                    # 使用批量分配
                    results = self.allocator.batch_allocate_tasks(allocation_requests)

                    # 处理分配结果并更新补贴池
                    for i, result in enumerate(results):
                        if result.success:
                            total_generated_tasks += len(result.allocated_tasks)

                            # 如果是按需生成，需要更新补贴池剩余金额
                            request = allocation_requests[i]
                            if request.get('on_demand', False) and result.allocated_tasks:
                                generated_amount = sum(Decimal(str(task['amount'])) for task in result.allocated_tasks)
                                pool = self.db.query(VirtualOrderPool).filter(
                                    VirtualOrderPool.student_id == request['student_id'],
                                    VirtualOrderPool.is_deleted == False
                                ).first()
                                if pool:
                                    pool.remaining_amount = request['total_amount'] - generated_amount
                                    pool.updated_at = datetime.now()

                    # 提交任务创建
                    self.db.commit()
                else:
                    # 使用原有方式生成任务
                    for request in allocation_requests:
                        # 检查是否为按需生成
                        on_demand = request.get('on_demand', False)

                        if on_demand:
                            # 按需生成任务
                            tasks = self.generate_on_demand_virtual_tasks_for_student(
                                request['student_id'],
                                request['student_name'],
                                request['total_amount']
                            )

                            # 更新补贴池剩余金额
                            if tasks:
                                generated_amount = sum(task.commission for task in tasks)
                                pool = self.db.query(VirtualOrderPool).filter(
                                    VirtualOrderPool.student_id == request['student_id'],
                                    VirtualOrderPool.is_deleted == False
                                ).first()
                                if pool:
                                    pool.remaining_amount = request['total_amount'] - generated_amount
                                    pool.updated_at = datetime.now()
                        else:
                            # 传统全量生成
                            tasks = self.generate_virtual_tasks_for_student(
                                request['student_id'],
                                request['student_name'],
                                request['total_amount']
                            )

                        for task in tasks:
                            self.db.add(task)

                        total_generated_tasks += len(tasks)

                    # 提交任务创建
                    self.db.commit()

            return {
                'import_batch': import_batch,
                'total_students': total_students,
                'total_subsidy': float(total_subsidy),
                'generated_tasks': total_generated_tasks,
                'use_service_allocation': use_service_allocation,
                'task_generation_enabled': generate_tasks
            }

        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"导入学生补贴数据失败: {str(e)}",
                data=None
            )

    def reallocate_student_tasks_with_service_allocation(self, student_id: int) -> Dict[str, Any]:
        """使用虚拟客服分配策略重新分配学生任务"""
        try:
            # 获取学生补贴池
            pool = self.db.query(VirtualOrderPool).filter(
                VirtualOrderPool.student_id == student_id,
                VirtualOrderPool.is_deleted == False
            ).first()

            if not pool:
                raise BusinessException(
                    code=404,
                    message="未找到该学生的补贴池",
                    data=None
                )

            if pool.remaining_amount <= 0:
                raise BusinessException(
                    code=400,
                    message="该学生没有剩余金额可分配",
                    data=None
                )

            # 删除该学生未接取的虚拟任务
            self.db.query(Tasks).filter(
                and_(
                    Tasks.is_virtual.is_(True),
                    Tasks.target_student_id == student_id,
                    Tasks.status == '0'
                )
            ).delete()

            # 使用新的分配策略重新生成任务
            result = self.generate_virtual_tasks_with_service_allocation(
                student_id, pool.student_name, pool.remaining_amount
            )

            # 更新补贴池信息
            pool.last_allocation_at = datetime.now()
            pool.updated_at = datetime.now()

            self.db.commit()

            return {
                'student_id': student_id,
                'remaining_amount': float(pool.remaining_amount),
                'allocation_result': result
            }

        except BusinessException:
            raise
        except Exception as e:
            self.db.rollback()
            raise BusinessException(
                code=500,
                message=f"重新分配学生任务失败: {str(e)}",
                data=None
            )

    def get_allocation_statistics(self) -> Dict[str, Any]:
        """获取虚拟客服分配统计信息"""
        try:
            return self.allocator.get_allocation_statistics()
        except Exception as e:
            raise BusinessException(
                code=500,
                message=f"获取分配统计失败: {str(e)}",
                data=None
            )

    # ================ 虚拟客服管理方法代理 ================

    def create_virtual_customer_service_v2(self, name: str, account: str,
                                         initial_password: str = "123456") -> Dict[str, Any]:
        """创建虚拟客服（使用新管理器）"""
        return self.service_manager.create_virtual_service(name, account, initial_password)

    def get_virtual_customer_services_v2(self, page: int = 1, size: int = 20,
                                       status: Optional[str] = None,
                                       include_stats: bool = True) -> Dict[str, Any]:
        """获取虚拟客服列表（使用新管理器）"""
        return self.service_manager.get_virtual_services(page, size, status, include_stats)

    def update_virtual_customer_service_v2(self, cs_id: int,
                                         update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新虚拟客服信息（使用新管理器）"""
        return self.service_manager.update_virtual_service(cs_id, update_data)

    def delete_virtual_customer_service_v2(self, cs_id: int) -> Dict[str, Any]:
        """删除虚拟客服并重新分配任务（使用新管理器）"""
        return self.service_manager.delete_virtual_service(cs_id)

    def batch_create_virtual_customer_services(self,
                                             services_data: List[Dict[str, str]]) -> Dict[str, Any]:
        """批量创建虚拟客服"""
        return self.service_manager.batch_create_virtual_services(services_data)

    def get_virtual_service_performance(self, cs_id: int, days: int = 30) -> Dict[str, Any]:
        """获取虚拟客服性能统计"""
        return self.service_manager.get_service_performance(cs_id, days)

    def process_completed_task_remaining_value(self, task_id: int) -> Dict[str, Any]:
        """
        处理已完成任务的剩余价值，重新生成新任务
        用于处理那些已经完成但没有处理剩余价值的任务

        Args:
            task_id: 已完成的任务ID

        Returns:
            Dict: 处理结果
        """
        try:
            # 查找已完成的虚拟任务
            task = self.db.query(Tasks).filter(
                and_(
                    Tasks.id == task_id,
                    Tasks.is_virtual.is_(True),
                    Tasks.status == '4'  # 已完成状态
                )
            ).first()

            if not task:
                return {
                    'success': False,
                    'message': f"未找到ID为{task_id}的已完成虚拟任务"
                }

            # 查找对应的学生补贴池
            pool = self.db.query(VirtualOrderPool).filter(
                VirtualOrderPool.student_id == task.target_student_id,
                VirtualOrderPool.is_deleted == False
            ).first()

            if not pool:
                return {
                    'success': False,
                    'message': f"未找到学生{task.target_student_id}的补贴池"
                }

            # 获取学生的返佣比例
            rebate_rate = self.get_student_rebate_rate(task.target_student_id)

            # 计算剩余任务价值
            student_actual_income = task.commission * rebate_rate
            remaining_task_value = task.commission - student_actual_income

            logger.info(f"处理任务{task_id}的剩余价值: 任务面值={task.commission}, "
                       f"返佣比例={rebate_rate}, 学生收入={student_actual_income}, "
                       f"剩余价值={remaining_task_value}")

            if remaining_task_value <= Decimal('0'):
                return {
                    'success': False,
                    'message': f"任务{task_id}没有剩余价值需要处理"
                }

            generated_tasks_info = []

            # 使用虚拟客服分配策略重新生成任务
            try:
                allocation_result = self.allocator.allocate_tasks_to_services(
                    remaining_task_value, task.target_student_id, pool.student_name
                )

                if allocation_result.success:
                    # 记录生成的任务信息
                    for allocated_task in allocation_result.allocated_tasks:
                        generated_tasks_info.append({
                            'task_id': allocated_task['id'],
                            'amount': allocated_task['amount'],
                            'founder_id': allocated_task['founder_id'],
                            'founder': allocated_task['founder']
                        })
                        logger.info(f"为剩余价值重新生成任务: ID={allocated_task['id']}, 金额={allocated_task['amount']}, "
                                   f"分配给客服: {allocated_task['founder']}")
                else:
                    logger.warning(f"使用虚拟客服分配策略处理剩余价值失败: {allocation_result.error_message}")
                    # 回退到原有方式（不分配虚拟客服）
                    new_task_amounts = self.calculate_task_amounts(remaining_task_value)
                    logger.info(f"回退到原有方式，剩余价值 {remaining_task_value} 分配为: {new_task_amounts}")

                    for amount in new_task_amounts:
                        new_task = self.create_virtual_task(task.target_student_id, pool.student_name, amount)
                        if new_task:
                            self.db.add(new_task)
                            generated_tasks_info.append({
                                'task_id': new_task.id,
                                'amount': float(amount)
                            })
                            logger.info(f"为剩余价值重新生成任务(无客服分配): ID={new_task.id}, 金额={amount}")
                        else:
                            logger.warning(f"图片资源不足，无法生成 {amount} 元的任务，停止生成")
                            break

            except Exception as e:
                logger.error(f"使用虚拟客服分配策略失败: {str(e)}，回退到原有方式")
                # 回退到原有方式
                new_task_amounts = self.calculate_task_amounts(remaining_task_value)
                logger.info(f"回退到原有方式，剩余价值 {remaining_task_value} 分配为: {new_task_amounts}")

                for amount in new_task_amounts:
                    new_task = self.create_virtual_task(task.target_student_id, pool.student_name, amount)
                    if new_task:
                        self.db.add(new_task)
                        generated_tasks_info.append({
                            'task_id': new_task.id,
                            'amount': float(amount)
                        })
                        logger.info(f"为剩余价值重新生成任务(回退方式): ID={new_task.id}, 金额={amount}")
                    else:
                        logger.warning(f"图片资源不足，无法生成 {amount} 元的任务，停止生成")
                        break

            self.db.commit()

            return {
                'success': True,
                'message': f"成功处理任务{task_id}的剩余价值",
                'original_task_id': task_id,
                'original_task_amount': float(task.commission),
                'student_actual_income': float(student_actual_income),
                'remaining_task_value': float(remaining_task_value),
                'generated_tasks': generated_tasks_info,
                'generated_count': len(generated_tasks_info)
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"处理任务{task_id}的剩余价值失败: {str(e)}")
            return {
                'success': False,
                'message': f"处理失败: {str(e)}"
            }

    def test_task_image_category_matching(self, sample_size: int = 100) -> Dict[str, Any]:
        """
        测试任务类型与图片分类的匹配效果（不入库）

        Args:
            sample_size: 测试样本数量

        Returns:
            Dict: 匹配测试结果
        """
        try:
            logger.info(f"开始测试任务类型与图片分类匹配，样本数量: {sample_size}")

            # 统计数据
            match_results = {
                'avatar_redesign': {'correct': 0, 'incorrect': 0, 'no_category': 0},
                'room_decoration': {'correct': 0, 'incorrect': 0, 'no_category': 0},
                'photo_extension': {'correct': 0, 'incorrect': 0, 'no_category': 0}
            }

            category_details = []

            for i in range(sample_size):
                # 生成任务内容
                task_content = self.generate_random_task_content()
                task_type = task_content.get('task_type', 'unknown')

                # 确定图片分类
                category_code = self._determine_image_category(task_content)

                # 记录详细信息
                detail = {
                    'index': i + 1,
                    'task_type': task_type,
                    'category_code': category_code,
                    'summary': task_content.get('summary', ''),
                    'match_status': 'unknown'
                }

                # 判断匹配状态
                if not category_code:
                    detail['match_status'] = 'no_category'
                    if task_type in match_results:
                        match_results[task_type]['no_category'] += 1
                elif task_type == category_code:
                    detail['match_status'] = 'correct'
                    if task_type in match_results:
                        match_results[task_type]['correct'] += 1
                else:
                    detail['match_status'] = 'incorrect'
                    if task_type in match_results:
                        match_results[task_type]['incorrect'] += 1

                category_details.append(detail)

            # 计算匹配率
            summary_stats = {}
            total_correct = 0
            total_samples = 0

            for task_type, stats in match_results.items():
                total = stats['correct'] + stats['incorrect'] + stats['no_category']
                if total > 0:
                    correct_rate = round((stats['correct'] / total) * 100, 2)
                    summary_stats[task_type] = {
                        'total_samples': total,
                        'correct_matches': stats['correct'],
                        'incorrect_matches': stats['incorrect'],
                        'no_category': stats['no_category'],
                        'correct_rate': correct_rate
                    }
                    total_correct += stats['correct']
                    total_samples += total

            overall_correct_rate = round((total_correct / total_samples) * 100, 2) if total_samples > 0 else 0

            result = {
                'test_info': {
                    'sample_size': sample_size,
                    'overall_correct_rate': overall_correct_rate,
                    'test_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                },
                'summary_stats': summary_stats,
                'detailed_results': category_details[:20],  # 只返回前20个详细结果
                'match_results': match_results
            }

            logger.info(f"匹配测试完成，总体正确率: {overall_correct_rate}%")
            return result

        except Exception as e:
            logger.error(f"测试任务类型与图片分类匹配失败: {str(e)}")
            return {
                'error': str(e),
                'test_info': {
                    'sample_size': 0,
                    'overall_correct_rate': 0,
                    'test_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }

    def _extract_room_type_from_filename(self, filename: str) -> Optional[str]:
        """
        从图片文件名中提取房间类型

        Args:
            filename: 图片原始文件名

        Returns:
            Optional[str]: 房间类型，如果无法识别则返回None
        """
        if not filename:
            return None

        # 房间类型关键词映射
        room_type_keywords = {
            '客厅': ['客厅'],
            '书房': ['书房'],
            '卧室': ['卧室', '主卧', '次卧', '儿童房'],
            '厨房': ['厨房'],
            '餐厅': ['餐厅'],
            '卫生间': ['卫生间', '浴室', '洗手间'],
            '阳台': ['阳台'],
            '玄关': ['玄关', '门厅'],
            '衣帽间': ['衣帽间', '衣柜间'],
            '储物间': ['储物间', '杂物间']
        }

        # 将文件名转换为小写进行匹配
        filename_lower = filename.lower()

        # 遍历房间类型关键词，寻找匹配
        for room_type, keywords in room_type_keywords.items():
            for keyword in keywords:
                if keyword in filename_lower:
                    return room_type

        # 如果没有找到匹配的关键词，返回None
        return None

    def _generate_room_decoration_content_with_room_type(self, room_type: str) -> Dict[str, str]:
        """
        根据房间类型生成装修风格任务内容

        Args:
            room_type: 房间类型

        Returns:
            Dict[str, str]: 任务内容
        """
        # 针对不同房间类型的装修风格变量
        room_specific_styles = {
            '客厅': ['现代简约', '北欧风格', '美式乡村', '新中式', '轻奢现代', '简约欧式'],
            '书房': ['新中式', '简约现代', '美式传统', '日式禅意', '工业风格', '北欧风格'],
            '卧室': ['现代简约', '北欧风格', '田园风格', '轻奢现代', '日式禅意', '法式浪漫'],
            '厨房': ['现代简约', '北欧风格', '美式乡村', '地中海风格', '工业风格', '简约欧式'],
            '餐厅': ['现代简约', '美式乡村', '新中式', '北欧风格', '法式浪漫', '轻奢现代'],
            '卫生间': ['现代简约', '北欧风格', '日式禅意', '轻奢现代', '地中海风格', '工业风格'],
            '阳台': ['现代简约', '田园风格', '地中海风格', '北欧风格', '日式禅意', '美式乡村'],
            '玄关': ['现代简约', '新中式', '轻奢现代', '北欧风格', '美式传统', '简约欧式'],
            '衣帽间': ['现代简约', '轻奢现代', '北欧风格', '美式传统', '简约欧式', '新中式'],
            '储物间': ['现代简约', '北欧风格', '工业风格', '日式禅意', '简约欧式', '美式乡村']
        }

        # 针对不同房间类型的氛围描述
        room_specific_moods = {
            '客厅': ['温馨', '舒适', '雅致', '大气', '温暖', '宁静'],
            '书房': ['宁静', '雅致', '专注', '文雅', '沉静', '清幽'],
            '卧室': ['温馨', '舒适', '宁静', '浪漫', '安逸', '私密'],
            '厨房': ['整洁', '实用', '温馨', '现代', '便利', '舒适'],
            '餐厅': ['温馨', '雅致', '舒适', '和谐', '温暖', '愉悦'],
            '卫生间': ['清洁', '现代', '舒适', '简洁', '实用', '明亮'],
            '阳台': ['清新', '自然', '舒适', '惬意', '明亮', '开阔'],
            '玄关': ['简洁', '大气', '实用', '雅致', '明亮', '整洁'],
            '衣帽间': ['整洁', '实用', '雅致', '现代', '舒适', '精致'],
            '储物间': ['整洁', '实用', '简洁', '现代', '便利', '有序']
        }

        # 获取房间特定的风格和氛围，如果没有则使用默认值
        styles = room_specific_styles.get(room_type, ['现代简约', '北欧风格', '美式乡村', '新中式', '轻奢现代', '简约欧式'])
        moods = room_specific_moods.get(room_type, ['温馨', '舒适', '雅致', '现代', '宁静', '和谐'])

        # 通用的技法和色彩
        techniques = ['空间布局', '色彩搭配', '材质选择', '灯光设计', '家具配置', '装饰点缀']
        colors = ['暖色调', '冷色调', '中性色', '对比色', '渐变色', '单色调']

        # 随机选择变量
        style = random.choice(styles)
        mood = random.choice(moods)
        technique = random.choice(techniques)
        color = random.choice(colors)

        # 生成房间特定的标题
        if hasattr(self, 'task_titles_data') and self.task_titles_data and 'room_decoration' in self.task_titles_data:
            # 从现有标题中选择一个，然后添加房间类型
            base_title = random.choice(self.task_titles_data['room_decoration'][:50])  # 取前50个
            title = f"{room_type}{style}风格设计"
        else:
            title = f"{room_type}{style}风格装修设计"

        # 生成房间特定的需求描述
        requirement_templates = [
            f'{room_type}装修风格：设计{style}风格{room_type}，重点处理{technique}，使用{color}作为主色调，确保空间{mood}实用，整体效果统一',
            f'{room_type}装修风格：制作{style}风格{room_type}方案，着重{technique}设计，采用{color}配色，注重{mood}性和美观性的平衡',
            f'{room_type}装修风格：规划{style}风格{room_type}设计，优化{technique}布局，运用{color}色彩搭配，满足{mood}需求和审美要求'
        ]

        requirement = random.choice(requirement_templates)

        return {
            'summary': title,
            'requirement': requirement,
            'task_type': 'room_decoration'
        }
