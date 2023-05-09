import json


def load_config():
    global config
    with open("config.json", "r") as file:
        return json.load(file)


def is_in_production():
    global config
    return config["production"]


def update_config(key: str, value: any):
    global config
    config[key] = value
    save_config()


def save_config():
    global config
    with open("config.json", "w") as file:
        json.dump(config, file, indent=4)


def config_completed_stage():
    global config
    stages = config["initialization"]["stages"]
    for stage in stages:
        if not stage["completed"]:
            return stage
    return None

def update_prerequisites_info(host, port, user, password):
    global config
    # Update the host and port values in the config dictionary
    config["database"]["host"] = host
    config["database"]["port"] = port
    config["database"]["user"] = user
    config["database"]["password"] = password
    # Save the updated config to the config.json file
    save_config()

def update_database_info(db_name, source_schema, marketing_schema, users_schema):
    global config
    config["database"]["db_name"] = db_name
    config["database"]["source_schema"] = source_schema
    config["database"]["marketing_schema"] = marketing_schema
    config["database"]["users_schema"] = users_schema
    # Save the updated config to the config.json file
    save_config()

def set_stage_completed(stage_name):
    global config
    for stage in config["initialization"]["stages"]:
        if stage["name"] == stage_name:
            stage["completed"] = True
            break
    save_config()


def increment_stage():
    global config
    index = 0
    stages = config["initialization"]["stages"]
    while stages[index]["completed"]:
        index += 1
    config["initialization"]["stage"] = index
    save_config()


def save_config():
    global config
    with open("config.json", "w") as file:
        json.dump(config, file)


config = load_config()

