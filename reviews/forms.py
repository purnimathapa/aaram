"""The review form shown on the product page."""
from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    # Show the rating as a 1-to-5 dropdown rather than a free number box.
    rating = forms.TypedChoiceField(
        choices=[(n, f"{n} star{'s' if n > 1 else ''}") for n in range(5, 0, -1)],
        coerce=int,
        label="Rating",
    )

    class Meta:
        model = Review
        fields = ["rating", "title", "body"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 4}),
        }
