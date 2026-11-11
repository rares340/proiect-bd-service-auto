class UserSession:
    _instance = None

    def __init__(self):
        self.id_utilizator = None
        self.nume_utilizator = None
        self.rol = None
        self.id_angajat = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = UserSession()
        return cls._instance

    def set_session(self, data: dict):
        self.id_utilizator = data.get("id_utilizator")
        self.nume_utilizator = data.get("nume_utilizator")
        self.rol = data.get("rol")
        self.id_angajat = data.get("id_angajat")

    def clear(self):
        self.id_utilizator = None
        self.nume_utilizator = None
        self.rol = None
        self.id_angajat = None

    def is_logged_in(self) -> bool:
        return self.id_utilizator is not None
