from django import forms

class CollectionForm(forms.Form):
    """Koleksiyon oluşturma ve düzenleme formu"""
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Koleksiyon Adı'})
    )
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Açıklama', 'rows': 3})
    )

class FileUploadForm(forms.Form):
    """Tekli dosya yükleme formu"""
    file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    collection = forms.ChoiceField(
        choices=[],  # Boş bırakıyoruz, view'da dolduracağız
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['collection'].choices = [(None, 'Ana Dizin')]  # Varsayılan seçenek

class BulkUploadForm(forms.Form):
    """Toplu dosya yükleme formu"""
    # Django'nun FileField'ı multiple dosya desteği için kullanılamıyor
    # Bu yüzden view'da request.FILES'dan dosyaları alacağız
    collection = forms.ChoiceField(
        choices=[],  # Boş bırakıyoruz, view'da dolduracağız
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['collection'].choices = []  # Varsayılan olarak boş

class FileEditForm(forms.Form):
    """Dosya düzenleme formu"""
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    collection = forms.ChoiceField(
        choices=[],  # Boş bırakıyoruz, view'da dolduracağız
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['collection'].choices = [(None, 'Ana Dizin')]  # Varsayılan seçenek 