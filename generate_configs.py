import copy
import json

BASE_CONFIG: dict[str, bool | int | float | str] = {
    "batch_size": 32,
    "max_evals_without_improving": 5,
    "max_iters": 8000,
    "n_test": 70000,
    "n_val": 10000,
}

SMALL_CONFIG: dict[str, bool | int | float | str] = {
    "batch_size": 64,
    "max_evals_without_improving": 10,
    "max_iters": 8000,
    "n_embd": 192,
    "n_head": 6,
    "n_layer": 3,
    "n_test": 70000,
    "n_val": 10000,
}


def n_train_str(n_train: int) -> str:
    if n_train % 1000 == 0:
        return f"{n_train // 1000}k"
    else:
        return f"{n_train / 1000}k"


if __name__ == "__main__":
    for n_train in [3750]:
        for decoder in [False]:
            for task in ["reversed_addition"]:
                for seed in range(3, 5):
                    name = f"{n_train_str(n_train)}_{task}_{'decoder' if decoder else 'encoder'}_{seed}"
                    config = copy.deepcopy(BASE_CONFIG)
                    config["n_train"] = n_train
                    config["decoder"] = decoder
                    config["task"] = task
                    config["seed"] = seed
                    config["name"] = name
                    config["results_dir"] = f"results/{n_train_str(n_train)}"

                    if n_train <= 5000:
                        config["max_loss_for_early_stopping"] = 1e9

                    config_path = f"configs/{name}.json"
                    with open(config_path, "w") as f:
                        json.dump(config, f)

    for n_train in [2500, 5000, 10000, 20000]:
        for decoder in [True, False]:
            for task in ["plain_addition", "reversed_addition"]:
                for seed in range(3, 5):
                    name = f"{n_train_str(n_train)}_{task}_small_{'decoder' if decoder else 'encoder'}_{seed}"
                    config = copy.deepcopy(SMALL_CONFIG)
                    config["n_train"] = n_train
                    config["decoder"] = decoder
                    config["task"] = task
                    config["seed"] = seed
                    config["name"] = name
                    config["results_dir"] = f"results/{n_train_str(n_train)}"

                    if n_train <= 5000:
                        config["max_loss_for_early_stopping"] = 1e9

                    config_path = f"configs/{name}.json"
                    with open(config_path, "w") as f:
                        json.dump(config, f)
