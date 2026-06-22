import os


def set_cred_environments():
    try:
        with open(".env", "r") as f:
            # NeonDB_URL = <>
            # DB_HOST = <>
            # DB_NAME = <>
            # DB_USER = <>
            # DB_PASSWORD = <>
            # DB_PORT = <>
            # DB_SSLMODE = <>
            # GEMINI_API_KEY = <>
            already_set = set()
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split(" = ")
                    if key in already_set:
                        os.environ[key] = os.environ[key] + ", " + value
                    else:
                        already_set.add(key)
                        os.environ[key] = value

    except FileNotFoundError:
        print("Error: $USER_DIR/secret/Creds not found")
        raise Exception("Environment variables not set")


if __name__ == "__main__":
    set_cred_environments()
    print(os.getenv("NeonDB_URL"))
