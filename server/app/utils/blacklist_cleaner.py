from datetime import datetime, timedelta
from ..model.blacklist import Blacklist
from .. import db
from config import access_token_expire_sec
def cleanup_expired_tokens(expiry_time: int = access_token_expire_sec):
    seconds = expiry_time  # ví dụ: xoá sau 3600 giây
    threshold = datetime.utcnow() - timedelta(seconds=seconds)

    deleted = db.session.query(Blacklist).filter(Blacklist.created_at < threshold).delete()
    db.session.commit()

    print(f"[Batch Job] Đã xoá {deleted} token hết hạn khỏi blacklist.")
