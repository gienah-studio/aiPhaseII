from sqlalchemy.orm import Session
from typing import List, Optional

from shared.models.user import User

class CRUDUser:
    async def get_by_enterprise(self, db: Session, *, enterprise_id: int) -> List[User]:
        return db.query(User).filter(User.enterprise_id == enterprise_id).all()

user = CRUDUser() 