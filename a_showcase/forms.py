from django import forms


class MultipleFileInput(forms.ClearableFileInput):
    """
    Widget that allows selecting multiple files.
    """

    allow_multiple_selected = True


class ShowcaseUploadForm(forms.Form):
    images = forms.ImageField(
        widget=MultipleFileInput(attrs={"multiple": True}),
        required=True,
    )


