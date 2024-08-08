import copy
import json

BASE_CONFIG: dict[str, bool | int | float | str] = {
    "max_iters": 8000,
    "n_test": 70000,
    "n_val": 10000,
}

if __name__ == "__main__":
    for n_train in [5000, 10000, 15000, 20000]:
        for decoder in [True]:
            for task in ["reversed_addition"]:
                for seed in range(5):
                    name = f"{n_train // 1000}k_{task}_{'decoder' if decoder else 'encoder'}_{seed}"
                    config = copy.deepcopy(BASE_CONFIG)
                    config["n_train"] = n_train
                    config["decoder"] = decoder
                    config["task"] = task
                    config["seed"] = seed
                    config["name"] = name
                    config["results_dir"] = f"results/{n_train // 1000}k"
                    
                    config_path = f"configs/{name}.json"
                    with open(config_path, "w") as f:
                        json.dump(config, f)
                    