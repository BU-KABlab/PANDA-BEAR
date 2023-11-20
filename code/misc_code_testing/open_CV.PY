import cv2

def get_webcam_image():
    # get frames from video caputer device
    cap = cv2.VideoCapture(0)

    # show the frames
    while(True):
        # Capture frame-by-frame
        ret, frame = cap.read()
        # Display the resulting frame
        cv2.imshow('frame',frame)
        # press q to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    # When everything done, release the capture
    cap.release()
    # close all windows
    cv2.destroyAllWindows()

def get_image_from_file():
    # read image from file
    img = cv2.imread('images/lena.jpg', 0)
    # show the image
    cv2.imshow('image', img)
    # wait for key press
    cv2.waitKey(0)
    # close all windows
    cv2.destroyAllWindows()

def take_image_with_FLIR():
    """running pycapture-test.py from python 3.11"""
    # Call FlyCapture2Test.py from python 3.11 using python 3.6 envrionment using subprocess
    import subprocess
    from pathlib import Path
    file_path = Path("C:\\Users\\Kab Lab\\anaconda3\\envs\\python360\\PyCapture2\\examples\\FlyCapture2Test.py")
    env_path = Path("C:\\Users\\Kab Lab\\anaconda3\\envs\\python360\\python.exe")
    subprocess.run([env_path, file_path], check= False, shell = True)

    ## Open the image in C:\Users\Kab Lab\Pictures\FLIR directory
    # read image from file
    img = cv2.imread('C:\\Users\\Kab Lab\\Pictures\\FLIR\\fc2TestImage.png', 0)
    # show the image
    cv2.imshow('image', img)
    # wait for key press
    cv2.waitKey(0)
    # close all windows
    cv2.destroyAllWindows()


if __name__ == "__main__":
    # get_webcam_image()
    # get_image_from_file()
    take_image_with_FLIR()