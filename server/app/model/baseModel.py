import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func, expression # Για server_default=func.now()
from sqlalchemy.dialects.postgresql import UUID
# Giả sử 'db' là SQLAlchemy instance và 'Base' là declarative base (thường là db.Model)
# được import từ package 'app' của bạn.
from .. import db, Base

class BaseModel(Base): # Kế thừa từ Base của ứng dụng
    """
    Lớp Model cơ sở chứa các trường và phương thức chung.
    SQLAlchemy sẽ không tạo bảng cho lớp này trong database.
    """
    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=expression.false()
    )

    def save(self, commit=True):
        db.session.add(self)
        if commit:
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise
        return self


    def delete_permanently(self):
        """Xóa vĩnh viễn instance hiện tại khỏi database."""
        try:
            db.session.delete(self)
            db.session.commit()
            return self
        except Exception as e:
            db.session.rollback()
            raise e

    def soft_delete(self):
        """Đánh dấu instance là đã bị xóa (soft delete)."""
        self.is_deleted = True
        # self.updated_at = datetime.utcnow() # onupdate của SQLAlchemy nên xử lý việc này
        db.session.add(self) # Đảm bảo session theo dõi thay đổi
        db.session.commit()
        return self

    def undelete(self):
        """Bỏ đánh dấu xóa cho instance."""
        self.is_deleted = False
        # self.updated_at = datetime.utcnow()
        db.session.add(self)
        db.session.commit()
        return self

    def update(self, **kwargs):
        """Cập nhật các thuộc tính của instance và commit."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key): # Kiểm tra xem thuộc tính có tồn tại không
                    setattr(self, key, value)
            # self.updated_at = datetime.utcnow() # onupdate nên xử lý việc này
            db.session.add(self)
            db.session.commit()
            return self
        except Exception as e:
            db.session.rollback()
            raise e

    def as_dict(self, exclude=None):
        """
        Trả về một dictionary đại diện cho model.
        Có thể loại trừ một số cột nhất định.
        Chuyển đổi datetime thành chuỗi ISO format.
        """
        if exclude is None:
            exclude = []
        
        data = {}
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                if isinstance(value, datetime):
                    data[column.name] = value.isoformat()
                elif isinstance(value, uuid.UUID): # Xử lý nếu id là UUID object
                    data[column.name] = str(value)
                else:
                    data[column.name] = value
        return data

    def __repr__(self):
        return f'<{self.__class__.__name__} id={self.id}>'
