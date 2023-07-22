import time
import sys

def print_loading_bar(iterations, total, bar_length=30):
    progress = iterations / total
    arrow_length = int(round(bar_length * progress))
    space_length = bar_length - arrow_length
    loading_bar = f"[{'=' * arrow_length}>{' ' * space_length}] {int(progress * 100)}%"

    panda_frames = [
        "(o^ω^o)", "(o^ω^o)", "(o~ω~o)", "(o・ε・o)", "(o･▽･o)", "(o･∀･o)", "(o･∀･o)人",
        "(人･∀･)", "(人･∀･)", "(人･ω･)", "(人･ω･)人", "(人･ω･) 人",
    ]

    panda_index = int(iterations / 2) % len(panda_frames)
    loading_bar += f" {panda_frames[panda_index]} Eating bamboo..."

    sys.stdout.write("\r" + loading_bar)
    sys.stdout.flush()

# Example usage
total_iterations = 100
for i in range(total_iterations + 1):
    print_loading_bar(i, total_iterations)
    time.sleep(0.1)

# Add a newline after the loading is complete
print("\nLoading complete!")
