import os
import re
import random
import datetime

import PIL
from PIL import Image
import bleach

import paths

###############################################################################
# app level defines
###############################################################################
MAX_UPLOAD_SIZE = 104857600  # (1024 * 1024 bits * 100)

THOUGHT_PREVIEW_IMAGE_SIZE = (600, 300)
IDEA_PREVIEW_IMAGE_SMALL_SIZE = (600, 150)
IDEA_PREVIEW_IMAGE_SIZE = (600, 300)

DEFAULT_TRUNCATE_LENGTH = 70
ALLOWED_TAGS = [
    'abbr', 'ul', 'blockquote', 'code', 'em', 'strong', 'li', 'ol',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'br'
]


###############################################################################
# methods and code common to entire blog app
###############################################################################
def slugify(source_str, max_len=20):
    """ create a nice slug given a string; FYI, Django comes with a prebuilt
        slugify function (django.template.defaultfilters) which handles
        non-unicode characters too, but doesn't truncate.

    :param source_str: string to make slug out of
    :param max_len: maximum length of slug
    :return: a string that is a valid slug
    """
    urlenc_regex = re.compile(r'[^a-z0-9\-_]+')
    str_words = source_str.lower().split(" ")

    counted_len = len(str_words[0])
    slug_tokens = [str_words.pop(0)]
    while str_words and counted_len + len(str_words[0]) <= max_len:
        counted_len += len(str_words[0])
        slug_tokens.append(str_words.pop(0))

    slug = "-".join(slug_tokens)
    slug = urlenc_regex.sub('', slug)
    return slug


def truncate(content, max_length=DEFAULT_TRUNCATE_LENGTH, allowed_tags=ALLOWED_TAGS, strip=True):
    """ truncate a body of text to the expected 'max_length' and strip
        the body of text of all html tags that are not in 'allowed tags'. You
        can also specify a 'strip' value (True -> strip html tags, False ->
        escape html tags and leave them in text)
    """

    truncated_str = bleach.clean(
        content,
        tags=allowed_tags,
        strip=strip,
        strip_comments=True,
    )

    truncated_str = truncated_str[:max_length]
    if max_length < len(content):
        truncated_str += "..."

    return truncated_str


def generate_upload_filename(filename):
    """ given a string (presumably an original filename with extension),
        generate a non-conflicting filename for user uploads
    """
    filename, ext = os.path.splitext(filename)
    filename = "%s-%s" % (datetime.datetime.now().strftime("%Y%m%d%H%M%S"), str(int(random.random() * 1000)))

    if ext == '.':
        ext = '.txt'

    return filename + ext


def upload_file(f):
    """ Given file post data, place filedata into media directory

        Watch out. This function will return True, file_url if the
        file already exists. This will point to the right url, but
        maybe not be the file you were expecting.

        Returns 2-tuple (Boolean, String)
          success -> True, file_url of newly created file
          failure -> False, error message
    """
    # determine correct folder depending on content_type
    content_category = f.content_type.split("/")[0]
    if content_category == "image":
        file_dir = paths.MEDIA_IMAGE_ROOT
    elif content_category == "video":
        file_dir = paths.MEDIA_VIDEO_ROOT
    else:
        file_dir = paths.MEDIA_FILE_ROOT

    file_url = os.path.join(file_dir, generate_upload_filename(f.name))

    # enforce file size limit
    if f.size > MAX_UPLOAD_SIZE:
        return False, "%s exceeds maximum upload size!" % f.name

    try:
        os.makedirs(file_dir)
    except OSError:
        # if there is a file with the same name as the intended directory,
        # fail, else directory exists and everything is ok
        if os.path.exists(file_dir) and not os.path.isdir(file_dir):
            return False, "%s cannot be created." % file_dir

    if os.path.exists(file_url):
        # file already exists, return file_url
        return True, file_url

    with open(file_url, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    return True, file_url


def get_center_coord(box, rect):
    """ given a tuple (x, y) "box" representing a rectangle where x is the
        width of the rectangle in pixels and y is the height, and another
        tuple "rect", return a coordinate pair (x_offset, y_offset) such that
        box will be centered inside rect.
    """
    return (max(0, int(float(rect[0] - box[0]) / 2)),
            max(0, int(float(rect[1] - box[1]) / 2)))


def resize_image(filename, new_size=THOUGHT_PREVIEW_IMAGE_SIZE):
    """ Given a filename to an existing image file, resize the
        file to the given dimensions (new_size). If no dimensions
        are provided, the file will be resized and cropped to the
        value in THOUGHT_PREVIEW_IMAGE_SIZE. The new image will
        be saved over the existing filename.
    """
    image = Image.open(filename)
    image_size = image.size

    if image_size[0] < new_size[0] or image_size[1] < new_size[1]:
        # find the smallest dimension, upscale, and crop
        resize_ratio = max(float(new_size[0]) / image_size[0],
                           float(new_size[1]) / image_size[1])
        image_size = (int(image_size[0] * resize_ratio),
                      int(image_size[1] * resize_ratio))
        image = image.resize(size=image_size, resample=PIL.Image.LANCZOS)
    elif image_size[0] > new_size[0] or image_size[1] > new_size[1]:
        # if the image is larger, find smallest edge, and shrink
        resize_ratio = max(float(new_size[0]) / image_size[0],
                           float(new_size[1]) / image_size[1])
        image_size = (int(image_size[0] * resize_ratio),
                      int(image_size[1] * resize_ratio))
        image = image.resize(size=image_size, resample=PIL.Image.LANCZOS)
    else:
        # image is already the perfect size, don't do anything
        return

    (offset_x, offset_y) = get_center_coord(new_size, image_size)
    crop_box = (offset_x, offset_y, offset_x + new_size[0], offset_y + new_size[1])

    cropped_image = image.crop(crop_box)
    cropped_image.save(filename, 'PNG')