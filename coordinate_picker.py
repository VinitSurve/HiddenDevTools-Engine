from PIL import Image
import matplotlib.pyplot as plt

img = Image.open("templates/Github_Content_Slide_Template.jpg")

fig, ax = plt.subplots(figsize=(8,10))
ax.imshow(img)

def onclick(event):
    if event.xdata and event.ydata:
        print(f"x={int(event.xdata)}, y={int(event.ydata)}")

cid = fig.canvas.mpl_connect("button_press_event", onclick)

plt.show()