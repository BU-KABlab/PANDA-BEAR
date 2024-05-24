"""Various functions for image processing."""

from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from epanda_lib.sql_tools import sql_utilities
from epanda_lib.experiment_class import ExperimentBase

# def add_data_zone(image: Image, experiment: ExperimentBase = None, context: str = None) -> Image:
#     """Adds a data zone to the bottom of the image."""
#     # Determine the size of the image
#     # Get the date and time from the image metadata
#     date_time = get_image_date_time(image, experiment)
#     banner_height = 100
#     banner = create_banner(image.width, banner_height)
#     drawn_banner = ImageDraw.Draw(banner)

#     draw_vertical_lines(drawn_banner, banner_height)

#     text_starts = calculate_text_starts(image.width)
#     segment_widths = [250, 250.0, 200.0, 150.0, 600.0, 175.0, 175.0, 200.0]

#     draw_logo(drawn_banner, text_starts[0], banner)
#     draw_epanda_pin(drawn_banner, text_starts[1], experiment.pin)
#     draw_date(drawn_banner, text_starts[2], date_time)
#     draw_project(drawn_banner, text_starts[3], experiment.project_id, experiment.project_campaign_id)
#     draw_experiment(drawn_banner, text_starts[4], experiment.experiment_id, context, text_starts, segment_widths)
#     draw_wellplate_well_id(drawn_banner, text_starts[5], experiment.plate_id, experiment.well_id)
#     draw_substrate_type(drawn_banner, text_starts[6], get_substrate(experiment))

#     image_with_banner = create_image_with_banner(image, banner, banner_height)
#     return image_with_banner

# def get_image_date_time(image: Image, experiment: ExperimentBase) -> datetime:
#     """Get the date and time from the image metadata."""
#     try:
#         # Check the image file type
#         if image.format == "TIFF":
#             tiff_tags = image.tag_v2
#             date_time = tiff_tags.get("DateTime")
#             if date_time is not None:
#                 date_time = datetime.strptime(date_time, "%Y:%m:%d %H:%M:%S")
#             else:
#                 # Fallback on file creation date if unable to get from metadata
#                 file_creation_time = datetime.fromtimestamp(Path(image.filename).stat().st_ctime)
#                 date_time = file_creation_time
#         else:
#             # Fallback on file creation date if unable to get from metadata
#             if experiment is None:
#                 date_time = datetime.now().isoformat(timespec="seconds")
#             else:
#                 file_creation_time = datetime.fromtimestamp(Path(image.filename).stat().st_ctime)
#                 date_time = file_creation_time
#         if isinstance(date_time, str):
#             date_time = datetime.fromisoformat(date_time)
#     except:
#         # Fallback on current time if all else fails
#         date_time = datetime.now().isoformat(timespec="seconds")
#     return date_time

# def create_banner(width: int, height: int) -> Image:
#     """Create a banner image with the specified width and height."""
#     return Image.new("RGB", (width, height), "black")

# def draw_vertical_lines(draw_banner: ImageDraw, banner_height: int) -> None:
#     """Draw vertical white lines to separate the segments."""
#     segment_widths = [250, 250.0, 200.0, 150.0, 600.0, 175.0, 175.0, 200.0]
#     segment_starts = [0] + [
#         round(sum(segment_widths[:i]), 0) for i in range(1, len(segment_widths))
#     ]

#     for segment_start in segment_starts[1:]:
#         draw_banner.line(
#             (segment_start, 0, segment_start, banner_height), fill="white", width=2
#         )

# def calculate_text_starts(width: int) -> list[int]:
#     """Calculate the starting x-coordinate for each text segment."""
#     segment_widths = [250, 250.0, 200.0, 150.0, 600.0, 175.0, 175.0, 200.0]
#     segment_starts = [0] + [
#         round(sum(segment_widths[:i]), 0) for i in range(1, len(segment_widths))
#     ]

#     # offset the segments to not touch the lines
#     text_starts = [segment + 5 for segment in segment_starts]
#     return text_starts

# def draw_logo(draw_banner: ImageDraw, epanda_logo_x: int, banner: Image) -> None:
#     """Draw the ePANDA logo on the banner."""
#     logo = Image.open(Path(__file__).parent.parent / "images" / "data_zone_logo.png")
#     logo = logo.resize((int(logo.width * 0.15), int(logo.height * 0.15)))
#     banner.paste(logo, (epanda_logo_x, 0))

# def draw_epanda_pin(draw_banner: ImageDraw, version_x: int, pin: str) -> None:
#     """Draw the ePANDA PIN on the banner."""
#     font = ImageFont.truetype("arial.ttf", 30)
#     draw_banner.text(
#         (version_x, 0), "ePANDA PIN", font=font, fill="white", align="center"
#     )
#     draw_banner.text(
#         (version_x, 30),
#         f"{pin[:10]}\n{pin[-11:]}",
#         font=ImageFont.truetype("arial.ttf", 20),
#         fill="white",
#         align="center",
#     )

# def draw_date(draw_banner: ImageDraw, date_x: int, date_time: datetime) -> None:
#     """Draw the date and time on the banner."""
#     font = ImageFont.truetype("arial.ttf", 30)
#     draw_banner.text((date_x, 0), "Date", font=font, fill="white", align="center")
#     draw_banner.text(
#         (date_x, 30),
#         date_time.strftime("%Y-%m-%d"),
#         font=font,
#         fill="white",
#         align="center",
#     )
#     draw_banner.text(
#         (date_x, 60),
#         date_time.strftime("%H:%M:%S"),
#         font=font,
#         fill="white",
#         align="center",
#     )

# def draw_project(draw_banner: ImageDraw, project_id_x: int, project_id: int, campaign_id: int) -> None:
#     """Draw the project ID on the banner."""
#     font = ImageFont.truetype("arial.ttf", 30)
#     draw_banner.text(
#         (project_id_x, 0), "Project", font=font, fill="white", align="center"
#     )
#     draw_banner.text(
#         (project_id_x, 30),
#         f"{str(project_id)}-{str(campaign_id)}",
#         font=font,
#         fill="white",
#         align="center",
#     )

# def draw_experiment(draw_banner: ImageDraw, experiment_id_x: int, experiment_id: int, context: str, segment_starts, segment_widths) -> None:
#     """Draw the experiment ID on the banner."""
#     font = ImageFont.truetype("arial.ttf", 30)
#     draw_banner.text(
#         (experiment_id_x, 0),
#         f"Experiment {str(experiment_id)}",
#         font=font,
#         fill="white",
#         align="center",
#     )
#     horizontal_line_x = segment_starts[4]
#     draw_banner.line(
#         (horizontal_line_x, 50, horizontal_line_x + segment_widths[4], 50),
#         fill="white",
#         width=2,
#     )
#     draw_banner.text(
#         (experiment_id_x, 60),
#         f"{str(context).capitalize()}",
#         font=font,
#         fill="white",
#         align="center",
#     )

# def draw_wellplate_well_id(draw_banner: ImageDraw, wellplate_well_id_x: int, wellplate_id: int, well_id: str) -> None:
#     """Draw the wellplate and well ID on the banner."""
#     font = ImageFont.truetype("arial.ttf", 30)
#     draw_banner.text(
#         (wellplate_well_id_x, 0), "Wellplate", font=font, fill="white", align="center"
#     )
#     draw_banner.text(
#         (wellplate_well_id_x, 30),
#         f"{str(wellplate_id)} - {well_id}",
#         font=font,
#         fill="white",
#         align="center",
#     )

# def draw_substrate_type(draw_banner: ImageDraw, substrate_type_x: int, substrate: str) -> None:
#     """Draw the substrate type on the banner."""
#     font = ImageFont.truetype("arial.ttf", 30)
#     draw_banner.text(
#         (substrate_type_x, 0), "Substrate", font=font, fill="white", align="center"
#     )
#     draw_banner.text(
#         (substrate_type_x, 30), f"{substrate}", font=font, fill="white", align="center"
#     )

# def create_image_with_banner(image: Image, banner: Image, banner_height: int) -> Image:
#     """Create a new image with the banner at the bottom."""
#     image_with_banner = Image.new(
#         "RGB", (image.width, image.height + banner_height), "white"
#     )
#     image_with_banner.paste(image, (0, 0))
#     image_with_banner.paste(banner, (0, image.height))
#     return image_with_banner

# def get_substrate(experiment: ExperimentBase) -> str:
#     """Get the substrate type from the database."""
#     try:
#         substrate = str(
#             sql_utilities.execute_sql_command(
#                 "SELECT substrate FROM well_types WHERE id = (SELECT type_id FROM wellplates WHERE id = ?)",
#                 (experiment.plate_id,),
#             )[0][0]
#         )
#     except:
#         substrate = "ITO"
#     return substrate


def add_data_zone(
    image: Image, experiment: ExperimentBase = None, context: str = None
) -> Image:
    """Adds a data zone to the bottom of the image."""
    # determin the size of the image
    # Get the date and time from the image metadata
    if experiment is None:
        pin = ""
        date_time = datetime.now().isoformat(timespec="seconds")
        project_id = ""
        campaign_id = ""
        experiment_id = ""
        wellplate_id = ""
        well_id = ""
        substrate = ""
    else:
        pin = experiment.pin
        date_time = experiment.status_date.isoformat(timespec="seconds")
        project_id = experiment.project_id
        campaign_id = experiment.project_campaign_id
        experiment_id = experiment.experiment_id
        wellplate_id = experiment.plate_id
        well_id = experiment.well_id

        try:
            substrate = str(
                sql_utilities.execute_sql_command(
                    "SELECT substrate FROM well_types WHERE id = (SELECT type_id FROM wellplates WHERE id = ?)",
                    (wellplate_id,),
                )[0][0]
            )
        except:
            substrate = "ITO"

    try:
        # Check the image file type
        if image.format == "TIFF":
            tiff_tags = image.tag_v2
            date_time = tiff_tags.get("DateTime")
            if date_time is not None:
                date_time = datetime.strptime(date_time, "%Y:%m:%d %H:%M:%S")
            else:
                # Fallback on file creation date if unable to get from metadata
                file_creation_time = datetime.fromtimestamp(
                    Path(image.filename).stat().st_ctime
                )
                date_time = file_creation_time
        else:
            # Fallback on file creation date if unable to get from metadata
            if experiment is None:
                date_time = datetime.now().isoformat(timespec="seconds")
            else:
                file_creation_time = datetime.fromtimestamp(
                    Path(image.filename).stat().st_ctime
                )
                date_time = file_creation_time
        if isinstance(date_time, str):
            date_time = datetime.fromisoformat(date_time)
    except:
        # Fallback on current time if all else fails
        date_time = datetime.now().isoformat(timespec="seconds")

    font = ImageFont.truetype("arial.ttf", 30)
    banner_height = 100
    banner = Image.new("RGB", (image.width, banner_height), "black")
    draw_banner = ImageDraw.Draw(banner)

    segment_widths = [250, 250.0, 200.0, 150.0, 600.0, 175.0, 175.0, 200.0]
    segment_starts = [0] + [
        round(sum(segment_widths[:i]), 0) for i in range(1, len(segment_widths))
    ]

    # draw vertical white lines to separate the segments
    for segment_start in segment_starts[1:]:
        draw_banner.line(
            (segment_start, 0, segment_start, banner_height), fill="white", width=2
        )

    # offset the segments to not touch the lines
    text_starts = [segment + 5 for segment in segment_starts]

    # ePANDA logo
    epanda_logo_x = text_starts[0]
    logo = Image.open(Path(__file__).parent.parent / "images" / "data_zone_logo.png")
    logo = logo.resize((int(logo.width * 0.15), int(logo.height * 0.15)))
    banner.paste(logo, (epanda_logo_x, 0))
    # ePANDA version
    version_x = text_starts[1]
    draw_banner.text(
        (version_x, 0), "ePANDA PIN", font=font, fill="white", align="center"
    )
    draw_banner.text(
        (version_x, 30),
        f"{pin[:10]}\n{pin[-11:]}",
        font=ImageFont.truetype("arial.ttf", 20),
        fill="white",
        align="center",
    )
    # date and time
    date_x = text_starts[2]
    draw_banner.text((date_x, 0), "Date", font=font, fill="white", align="center")
    draw_banner.text(
        (date_x, 30),
        date_time.strftime("%Y-%m-%d"),
        font=font,
        fill="white",
        align="center",
    )
    draw_banner.text(
        (date_x, 60),
        date_time.strftime("%H:%M:%S"),
        font=font,
        fill="white",
        align="center",
    )
    # project id
    project_id_x = text_starts[3]
    draw_banner.text(
        (project_id_x, 0), "Project", font=font, fill="white", align="center"
    )
    draw_banner.text(
        (project_id_x, 30),
        f"{str(project_id)}-{str(campaign_id)}",
        font=font,
        fill="white",
        align="center",
    )

    # experiment id
    experiment_id_x = text_starts[4]
    draw_banner.text(
        (experiment_id_x, 0),
        f"Experiment {str(experiment_id)}",
        font=font,
        fill="white",
        align="center",
    )
    horizontal_line_x = segment_starts[4]
    draw_banner.line(
        (horizontal_line_x, 50, horizontal_line_x + segment_widths[4], 50),
        fill="white",
        width=2,
    )
    draw_banner.text(
        (experiment_id_x, 60),
        f"{str(context).capitalize()}",
        font=font,
        fill="white",
        align="center",
    )

    # wellplate and well id
    wellplate_well_id_x = text_starts[5]
    draw_banner.text(
        (wellplate_well_id_x, 0), "Wellplate", font=font, fill="white", align="center"
    )
    draw_banner.text(
        (wellplate_well_id_x, 30),
        f"{str(wellplate_id)} - {well_id}",
        font=font,
        fill="white",
        align="center",
    )

    # substrate type
    substrate_type_x = text_starts[6]
    draw_banner.text(
        (substrate_type_x, 0), "Substrate", font=font, fill="white", align="center"
    )
    draw_banner.text(
        (substrate_type_x, 30), f"{substrate}", font=font, fill="white", align="center"
    )

    image_with_banner = Image.new(
        "RGB", (image.width, image.height + banner_height), "white"
    )
    image_with_banner.paste(image, (0, 0))
    image_with_banner.paste(banner, (0, image.height))
    return image_with_banner


def invert_image(image_path: str) -> str:
    """Inverts the colors of an image."""
    image_path: Path = Path(image_path)
    # Open the original image
    with Image.open(image_path) as img:
        # Convert the image to RGBA if it's not already in that mode
        img = img.convert("RGBA")

        # Extract the data
        datas = img.getdata()

        fully_inverted_data = []
        for item in datas:
            # Invert the colors, changing black to white and vice versa
            if item[0] in list(range(200, 256)):  # white and shades close to white
                fully_inverted_data.append((0, 0, 0, item[3]))  # change to black
            elif item[0] in list(range(0, 56)):  # black and shades close to black
                fully_inverted_data.append((255, 255, 255, item[3]))  # change to white
            else:
                # For other colors, just invert the RGB values
                fully_inverted_data.append(
                    (255 - item[0], 255 - item[1], 255 - item[2], item[3])
                )

        # Update image data with the fully inverted colors
        img.putdata(fully_inverted_data)

        # Save the new image with full color inversion
        fully_inverted_image_path = (
            image_path.parent / f"{image_path.stem}_fully_inverted{image_path.suffix}"
        )
        img.show()
        img_save = input("Do you want to save the fully inverted image? (y/n): ")
        if img_save.lower() == "y":
            img.save(fully_inverted_image_path)

    return fully_inverted_image_path


if __name__ == "__main__":
    test_image = Image.open(
        r"C:\Users\Gregory Robben\SynologyDrive\Downloads\16_2_10000596_G8_before_deposition_image_0.tiff"
    )
    # pin = "201010102040500000101"
    # date_time = "2021-01-01 12:00:00"
    # project_id = 16
    # campaign_id = 2
    # experiment_id = 10000596
    # wellplate_id = 107
    # well_id = "G8"
    # context = "before deposition"
    # substrate = "ITO"

    new_image = add_data_zone(
        experiment=None, image=test_image, context="before deposition"
    )
    new_image.show()
    new_image.save(
        r"C:\Users\Gregory Robben\SynologyDrive\Downloads\16_2_10000596_G8_before_deposition_image_0_with_banner.tiff"
    )

    # inverted_image_path = invert_image(r"images\PANDA_logo.png")
