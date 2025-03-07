import psycopg2
from bcrypt import checkpw
import bcrypt

class Auth:
    def __init__(self, db_config):
        """
        Initializes the mapper and sets up database connection.

        Args:
            db_config (dict): A dictionary containing database connection parameters.
        """
        self.conn = psycopg2.connect(**db_config)
        self.conn.autocommit = True
        self.cursor = self.conn.cursor()
        self.admin_username = "admin"
        self.admin_password_hash = bcrypt.hashpw(b"admin", bcrypt.gensalt())

    def verify_password(self, plain_password, hashed_password):
        """
        Verifies a plain text password against a hashed password.

        Args:
            plain_password (str): The plain text password.
            hashed_password (str): The hashed password from the database.

        Returns:
            bool: True if the password matches, False otherwise.
        """
        return checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

    def authenticate_user(self, email, plain_password):
        """
        Authenticates a user by verifying their email and password.

        Args:
            email (str): The user's email address.
            plain_password (str): The plain text password entered by the user.

        Returns:
            tuple: A tuple containing a boolean indicating if authentication is successful
                and the user's ID if successful, or None otherwise.
        """

        self.cursor.execute("SELECT user_id, password FROM users WHERE email = %s", (email,))
        result = self.cursor.fetchone()
        
        if result is None:
            return False, None  # Email not found

        user_id, hashed_password = result
        if self.verify_password(plain_password, hashed_password):
            return True, user_id  # Authentication successful
        
        return False, None  # Authentication failed

    def authenticate_admin(self, username, plain_password):
        if username == self.admin_username:
            return bcrypt.checkpw(plain_password.encode(), self.admin_password_hash)
        return False

    
