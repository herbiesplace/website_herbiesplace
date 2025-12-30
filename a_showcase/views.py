from io import BytesIO

from django.core.files.base import ContentFile
from django.shortcuts import redirect, render
from PIL import Image

from .forms import ShowcaseUploadForm
from .models import ShowcaseImage


def _resize_shortest_side(file_obj, target: int = 1920) -> ContentFile:
    """
    Resize an image so that its shortest side is `target` pixels,
    keeping aspect ratio. Returns a ContentFile ready to be saved.
    """
    img = Image.open(file_obj)
    img = img.convert("RGB")

    width, height = img.size
    shortest = min(width, height)

    if shortest == target:
        # no resizing needed, but normalise to JPEG
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=90)
        buffer.seek(0)
        return ContentFile(buffer.read())

    scale = target / shortest
    new_size = (int(width * scale), int(height * scale))
    img = img.resize(new_size, Image.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    buffer.seek(0)
    return ContentFile(buffer.read())


def showcase_list(request):
    images = ShowcaseImage.objects.all()
    return render(request, "a_showcase/showcase_list.html", {"images": images})


def showcase_upload(request):
    if request.method == "POST":
        form = ShowcaseUploadForm(request.POST, request.FILES)
        if form.is_valid():
            for f in request.FILES.getlist("images"):
                processed = _resize_shortest_side(f, target=1920)
                base_name = f.name.rsplit(".", 1)[0]
                filename = f"{base_name}_1920.jpg"
                obj = ShowcaseImage()
                obj.image.save(filename, processed, save=True)
            if request.htmx:
                images = ShowcaseImage.objects.all()
                return render(
                    request,
                    "a_showcase/partials/showcase_grid.html",
                    {"images": images},
                )
            return redirect("showcase:list")
    else:
        form = ShowcaseUploadForm()

    return render(
        request,
        "a_showcase/showcase_upload.html",
        {
            "form": form,
        },
    )


