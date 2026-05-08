import argparse

from classifier_training.ablation_trainer import Ablation

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config_path", type=str, required=True)
    args = parser.parse_args()
    ablation = Ablation(args.config_path)
    ablation.run_ablation()
    print("Ablation complete.")
