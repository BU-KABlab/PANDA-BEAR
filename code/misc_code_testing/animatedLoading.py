import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import time

def animate_loading_bar():
    fig, ax = plt.subplots()
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 1)
    ax.set_xlabel('Loading...')
    ax.set_xticks([])
    ax.set_yticks([])
    loading_bar = ax.bar(0, 0, width=1, align='center', color='blue')

    def update(frame):
        loading_bar[0].set_height(frame / 100)
        return loading_bar

    def init():
        return loading_bar

    def eat_bamboo(frame):
        # Panda eating bamboo ASCII art
        panda_eating = [
            "  🐼 🎋 ",
            "  \\   /",
            "   \\\'/ ",
            "    V  "
        ]

        # Clear previous lines (if any)
        print("\033[F" * len(panda_eating), end="")

        # Print the panda eating bamboo
        for line in panda_eating:
            print(line)

    frames = range(101)

    # Call eat_bamboo function every frame to show the animation
    for frame in frames:
        time.sleep(0.1)
        eat_bamboo(frame)

    anim = FuncAnimation(fig, update, frames=frames, init_func=init, blit=True)

    plt.show()

if __name__ == "__main__":
    animate_loading_bar()