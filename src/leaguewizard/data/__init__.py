from importlib.resources import files

image_path = str(files("leaguewizard.data.images").joinpath("logo.ico"))


__all__ = ["image_path"]
