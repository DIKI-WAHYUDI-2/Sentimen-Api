from apps.app import db

class News(db.Model):
    __tablename__ = 'berita'
    id = db.Column(db.Integer, primary_key=True)
    judul = db.Column(db.String(255), nullable=False)
    tanggal = db.Column(db.Date, nullable=False)
    sumber = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255), nullable=False)
    meta_title = db.Column(db.String(255), nullable=True)
    meta_description = db.Column(db.String(255), nullable=True)
    sentimen = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'judul': self.judul,
            'tanggal': self.tanggal.isoformat() if self.tanggal else None,
            'sumber': self.sumber,
            'link': self.link,
            'meta_title': self.meta_title,
            'meta_description': self.meta_description,
            'sentimen': self.sentimen,
        }