from apps.app import db


class News(db.Model):
    __tablename__ = "news"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    published_at = db.Column(db.Date, nullable=False)
    source = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=True)
    sentiment = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        published_date = self.published_at.isoformat() if self.published_at else None
        return {
            "id": self.id,
            "title": self.title,
            "published_at": published_date,
            "source": self.source,
            "url": self.url,
            "content": self.content,
            "sentiment": self.sentiment,
        }
