def mount_drive_if_colab():
    try:
        import google.colab
        from google.colab import drive

        drive.mount("/content/drive")
        print("Drive mounted (Colab)")
    except ImportError:
        print("Not running in Colab")
