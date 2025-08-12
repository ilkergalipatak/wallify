from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.conf import settings
import os
import shutil
import requests
import json
import logging
import datetime
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect
from django.urls import reverse

from .forms import CollectionForm, FileUploadForm, BulkUploadForm, FileEditForm
from .utils import (
    get_collections_from_api, get_files_from_api, 
    create_collection, delete_collection, 
    upload_file, delete_file, rename_file, move_file,
    scan_cdn_folder, get_file_info,
    api_upload_file, api_bulk_upload, api_delete_file, api_delete_collection, api_update_collection,
    convert_docker_url_to_browser_url, api_create_collection, clear_cache
)

# Logger tanımla
logger = logging.getLogger(__name__)

# CDN API kimlik doğrulama için yardımcı fonksiyonlar
def api_login(username, password):
    """CDN API'ye login isteği gönderir"""
    try:
        api_url = f"{settings.CDN_API_URL}/auth"
        logger.info(f"API login isteği gönderiliyor: {api_url}")
        response = requests.post(
            api_url,
            json={"login": username, "password": password}
        )
        if response.status_code == 200:
            logger.info("API login başarılı")
            return response.json()
        else:
            logger.error(f"API login hatası: HTTP {response.status_code}, Yanıt: {response.text}")
            return None
    except Exception as e:
        logger.error(f"API login hatası: {str(e)}")
        return None

@csrf_exempt
def login_view(request):
    """Login görünümü - CDN API ile kimlik doğrulama yapar"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # CDN API'ye istek gönder
        api_response = api_login(username, password)
        
        if api_response:
            # API'den token ve kullanıcı bilgilerini al
            token = api_response.get('token')
            api_key = api_response.get('api_key')
            user_id = api_response.get('user_id')
            
            # Session'a API bilgilerini kaydet
            request.session['api_token'] = token
            request.session['api_key'] = api_key
            request.session['user_id'] = user_id
            request.session['username'] = username
            
            messages.success(request, f"Hoş geldiniz, {username}!")
            return redirect('dashboard:home')
        else:
            messages.error(request, "Geçersiz kullanıcı adı veya şifre.")
    
    return render(request, 'dashboard/login.html')

def logout_view(request):
    """Logout görünümü - Session'dan API bilgilerini temizler"""
    # Session'dan API bilgilerini temizle
    if 'api_token' in request.session:
        del request.session['api_token']
    if 'api_key' in request.session:
        del request.session['api_key']
    if 'user_id' in request.session:
        del request.session['user_id']
    if 'username' in request.session:
        del request.session['username']
    
    messages.success(request, "Başarıyla çıkış yaptınız.")
    return redirect('login')

# API token kontrolü için decorator
def api_login_required(view_func):
    """API token kontrolü yapar, geçerli değilse login sayfasına yönlendirir"""
    def wrapper(request, *args, **kwargs):
        if 'api_token' not in request.session:
            messages.error(request, "Bu sayfayı görüntülemek için giriş yapmalısınız.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

@api_login_required
def home(request):
    """Ana sayfa görünümü (istatistikler Flask API'den alınır)"""
    api_token = request.session.get('api_token')
    api_url = f"{settings.CDN_API_URL}/admin/stats"
    try:
        response = requests.get(api_url, headers={'Authorization': api_token})
        stats = response.json() if response.status_code == 200 else {}
    except Exception as e:
        stats = {}
        logger.error(f"API stats çekilemedi: {str(e)}")

    # Okunaklı boyut formatı
    total_size = stats.get('total_size', 0)
    try:
        size = float(total_size)
    except (ValueError, TypeError):
        size = 0
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024 or unit == 'GB':
            total_size_str = f"{size:.2f} {unit}"
            break
        size /= 1024

    # recent_files url'lerine token ekle
    recent_files = stats.get('recent_files', [])
    token = request.session.get('api_token')
    for file in recent_files:
        if 'url' in file and token:
            if '?' in file['url']:
                file['url'] += f"&token={token}"
            else:
                file['url'] += f"?token={token}"

    context = {
        'collection_count': stats.get('collection_count', 0),
        'file_count': stats.get('total_files', 0),
        'total_size': total_size_str,
        'recent_files': recent_files,
        'collections': stats.get('top_collections', []),
        'username': request.session.get('username'),
    }
    return render(request, 'dashboard/home.html', context)

@api_login_required
def collection_list(request):
    """Koleksiyon listesi görünümü"""
    # API'den koleksiyonları al
    collections_data = get_collections_from_api(request.session.get('api_token'))
    
    # API'den tüm dosyaları tek seferde al
    all_files_data = get_files_from_api(token=request.session.get('api_token'))
    all_files = all_files_data.get('files', [])
    
    # Her koleksiyon için dosya sayısını hesapla
    collections = []
    for collection in collections_data:
        # Koleksiyona ait dosya sayısını hesapla
        collection_name = collection.get('name', '')
        collection_id = collection.get('id', '')
        file_count = collection.get('file_count', 0)
        total_size = collection.get('total_file_size', 0)
        
        # Okunaklı formata dönüştür
        size = total_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024 or unit == 'GB':
                readable_size = f"{size:.2f} {unit}"
                break
            size /= 1024
        
        # Tarihleri datetime objesine dönüştür
        created_at = collection.get('created_at')
        if created_at:
            try:
                created_at = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                created_at = None
        
        collections.append({
            'name': collection_name,
            'id': collection_id,
            'file_count': file_count,
            'total_size': readable_size,
            'created_at': created_at
        })
    
    context = {
        'collections': collections,
        'username': request.session.get('username'),
    }
    
    return render(request, 'dashboard/collection_list.html', context)

@api_login_required
def collection_create(request):
    """Koleksiyon oluşturma görünümü (sadece API üzerinden)"""
    if request.method == 'POST':
        form = CollectionForm(request.POST)
        if form.is_valid():
            collection_name = form.cleaned_data['name']
            
            # Sadece API'ye koleksiyon oluşturma isteği gönder
            api_result = api_create_collection(collection_name, request.session.get('api_token'))
            print(f"API yanıtı: {api_result}")
            
            if api_result.get('success', False):
                messages.success(request, f"'{collection_name}' koleksiyonu başarıyla oluşturuldu.")
                clear_cache()
                return redirect('dashboard:collection_list')
            else:
                error_msg = api_result.get('message', api_result.get('error', 'Bilinmeyen hata'))
                messages.error(request, f"Koleksiyon oluşturulurken bir hata oluştu: {error_msg}")
    else:
        form = CollectionForm()
    
    context = {
        'form': form,
        'title': 'Yeni Koleksiyon Oluştur',
        'username': request.session.get('username'),
    }
    
    return render(request, 'dashboard/collection_form.html', context)

# Diğer tüm view fonksiyonlarında login_required yerine api_login_required kullan
# ve context'e username ekle
@api_login_required
def collection_edit(request, pk):
    """Koleksiyon düzenleme görünümü (sadece isim güncellenebilir)"""
    # Tüm koleksiyonları al
    collections_data = get_collections_from_api(request.session.get('api_token'))
    
    # pk indeksine göre koleksiyon adını bul
    try:
        if not collections_data or pk <= 0 or pk > len(collections_data):
            raise IndexError("Invalid collection index")
        collection = collections_data[int(pk) - 1]  # pk 1'den başlıyor varsayalım
        collection_name = collection.get('name', '')
    except (IndexError, ValueError):
        messages.error(request, "Koleksiyon bulunamadı.")
        return redirect('dashboard:collection_list')
    
    if request.method == 'POST':
        form = CollectionForm(request.POST)
        if form.is_valid():
            new_collection_name = form.cleaned_data['name']
            # Sadece isim değişikliği API'ye gönderilecek
            if collection_name != new_collection_name:
                result = api_update_collection(collection_name, new_collection_name, request.session.get('api_token'))
                if result.get('success', False):
                    messages.success(request, f"'{new_collection_name}' koleksiyonu başarıyla güncellendi.")
                    return redirect('dashboard:collection_list')
                else:
                    messages.error(request, f"Koleksiyon güncellenirken bir hata oluştu: {result.get('error', 'Bilinmeyen hata')}")
            else:
                messages.success(request, f"'{new_collection_name}' koleksiyonu başarıyla güncellendi.")
                return redirect('dashboard:collection_list')
    else:
        # Form için sadece isim alanını göster
        form = CollectionForm(initial={'name': collection_name})
    
    context = {
        'form': form,
        'collection': {'name': collection_name},
        'title': 'Koleksiyonu Düzenle',
        'username': request.session.get('username'),
        'pk': pk,  # pk değişkenini context'e ekle
    }
    
    return render(request, 'dashboard/collection_form.html', context)

@api_login_required
def collection_delete(request, pk):
    """Koleksiyon silme görünümü"""
    # Collection list view'ı ile aynı mantığı kullan
    collections_data = get_collections_from_api(request.session.get('api_token'))
    
    # Debug log
    logger.info(f"Collection delete - pk: {pk}, collections count: {len(collections_data)}")
    
    # pk indeksine göre koleksiyon bilgilerini bul
    try:
        if not collections_data or pk <= 0 or pk > len(collections_data):
            raise IndexError("Invalid collection index")
        
        collection_data = collections_data[int(pk) - 1]  # pk 1'den başlıyor varsayalım
        collection_name = collection_data.get('name', '')
        logger.info(f"Found collection: {collection_name}, data: {collection_data}")
        
        if not collection_name:
            messages.error(request, "Koleksiyon adı bulunamadı.")
            return redirect('dashboard:collection_list')
    except (IndexError, ValueError) as e:
        logger.error(f"Collection not found - pk: {pk}, error: {e}")
        messages.error(request, "Koleksiyon bulunamadı.")
        return redirect('dashboard:collection_list')
    
    if request.method == 'POST':
        # API ile koleksiyonu sil
        result = api_delete_collection(collection_name, request.session.get('api_token'))
        
        if result.get('success', False):
            messages.success(request, f"'{collection_name}' koleksiyonu başarıyla silindi.")
            return redirect('dashboard:collection_list')
        else:
            error_msg = result.get('error', 'Bilinmeyen hata')
            messages.error(request, f"Koleksiyon silinirken bir hata oluştu: {error_msg}")
            return redirect('dashboard:collection_list')
    
    # collection_data zaten yukarıda alındı, tekrar aramaya gerek yok
    
    # Toplam boyutu okunaklı formata dönüştür
    total_size = collection_data.get('total_file_size', 0)
    readable_size = "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if total_size < 1024 or unit == 'GB':
            readable_size = f"{total_size:.2f} {unit}"
            break
        total_size /= 1024
    
    # Tarihleri datetime objesine dönüştür
    created_at = collection_data.get('created_at')
    updated_at = collection_data.get('updated_at')
    
    if created_at:
        try:
            created_at = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except:
            created_at = None
    
    if updated_at:
        try:
            updated_at = datetime.datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        except:
            updated_at = None
    
    context = {
        'collection': {
            'name': collection_name,
            'file_count': collection_data.get('file_count', 0),
            'total_size': readable_size,
            'created_at': created_at,
            'updated_at': updated_at
        },
        'pk': pk,
    }
    
    return render(request, 'dashboard/collection_confirm_delete.html', context)

@api_login_required
def collection_detail(request, pk):
    """Koleksiyon detay görünümü"""
    # Koleksiyonlar artık API'den geliyor, bu yüzden pk parametresi yerine
    # koleksiyon id'sini veya adını kullanacağız
    
    # Tüm koleksiyonları al
    collections_data = get_collections_from_api(request.session.get('api_token'))
    
    # pk indeksine göre koleksiyon bilgilerini bul
    collection_found = False
    collection_data = None
    
    try:
        # Önce id'ye göre ara
        for collection in collections_data:
            if collection.get('id') == pk:
                collection_data = collection
                collection_found = True
                break
        
        # Bulunamadıysa indekse göre ara
        if not collection_found:
            collection_data = collections_data[int(pk) - 1]  # pk 1'den başlıyor varsayalım
            collection_found = True
    except (IndexError, ValueError):
        messages.error(request, "Koleksiyon bulunamadı.")
        return redirect('dashboard:collection_list')
    
    collection_name = collection_data.get('name')
    collection_id = collection_data.get('id')
    
    # Koleksiyona ait dosyaları API'den al
    files_data = get_files_from_api(token=request.session.get('api_token'), collection=collection_name)
    files = files_data.get('files', [])
    
    # Dosya URL'lerine token ekle
    token = request.session.get('api_token')
    files_with_token = []
    for file_info in files:
        # Docker içindeki URL'yi tarayıcıda çalışacak şekilde dönüştür
        file_url = file_info.get('url', '')
        browser_url = convert_docker_url_to_browser_url(file_url)
        
        # Dosya boyutunu okunaklı formata dönüştür
        file_size = file_info.get('file_size', 0)
        size = file_size
        readable_size = "0 B"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024 or unit == 'GB':
                readable_size = f"{size:.2f} {unit}"
                break
            size /= 1024
        
        # Dosya türünü belirle
        file_name = file_info.get('file_name', '')
        _, ext = os.path.splitext(file_name)
        is_image = ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        
        files_with_token.append({
            'url': f"{browser_url}?token={token}",
            'name': file_name,
            'size': readable_size,
            'id': file_info.get('id', ''),
            'is_image': is_image
        })
    
    # Sayfalama
    paginator = Paginator(files_with_token, 20)  # Her sayfada 50 dosya
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Collection bilgilerini hazırla
    collection_info = {
        'name': collection_name,
        'id': collection_id,
        'file_count': collection_data.get('file_count', 0),
        'total_size': collection_data.get('total_file_size', 0),
        'created_at': collection_data.get('created_at'),
        'updated_at': collection_data.get('updated_at'),
        'description': collection_data.get('description', '')
    }
    
    # Toplam boyutu okunaklı formata dönüştür
    total_size = collection_info['total_size']
    for unit in ['B', 'KB', 'MB', 'GB']:
        if total_size < 1024 or unit == 'GB':
            collection_info['total_size'] = f"{total_size:.2f} {unit}"
            break
        total_size /= 1024
    
    # Tarihleri datetime objesine dönüştür
    if collection_info['created_at']:
        try:
            collection_info['created_at'] = datetime.datetime.fromisoformat(collection_info['created_at'].replace('Z', '+00:00'))
        except:
            collection_info['created_at'] = None
    
    if collection_info['updated_at']:
        try:
            collection_info['updated_at'] = datetime.datetime.fromisoformat(collection_info['updated_at'].replace('Z', '+00:00'))
        except:
            collection_info['updated_at'] = None
    
    context = {
        'collection': collection_info,
        'files': page_obj,
        'pk': pk,  # pk değişkenini context'e ekle
        'username': request.session.get('username'),
    }
    
    return render(request, 'dashboard/collection_detail.html', context)

@api_login_required
def file_list(request):
    """Dosya listesi görünümü"""
    # Filtreleme parametreleri
    collection_filter = request.GET.get('collection')
    search_query = request.GET.get('search')
    
    # API'den dosyaları al
    files_data = get_files_from_api(token=request.session.get('api_token'), collection=collection_filter)
    files = files_data.get('files', [])
    
    # Dosya URL'lerini işle ve gerekli formata dönüştür
    token = request.session.get('api_token')
    processed_files = []
    
    for file_info in files:
        # Docker içindeki URL'yi tarayıcıda çalışacak şekilde dönüştür
        file_url = file_info.get('url', '')
        browser_url = convert_docker_url_to_browser_url(file_url)
        
        # Dosya adını ve koleksiyon adını al
        file_name = file_info.get('file_name', '')
        collection_name = file_info.get('collection_name', '')
        file_size = file_info.get('file_size', 0)
        file_id = file_info.get('id', '')
        
        # Dosya uzantısından türünü belirle
        _, ext = os.path.splitext(file_name)
        is_image = ext.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        
        # Arama filtresi varsa ve dosya adında geçmiyorsa atla
        if search_query and search_query.lower() not in file_name.lower():
            continue
        
        # Okunaklı boyut formatı
        size = file_size
        readable_size = "0 B"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024 or unit == 'GB':
                readable_size = f"{size:.2f} {unit}"
                break
            size /= 1024
        
        processed_files.append({
            'id': file_id,
            'name': file_name,
            'collection': collection_name,
            'size': readable_size,
            'url': f"{browser_url}?token={token}",
            'is_image': is_image
        })
    
    # Sayfalama
    paginator = Paginator(processed_files, 20)  # Her sayfada 50 dosya
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Koleksiyon listesini API'den al
    collections = get_collections_from_api(request.session.get('api_token'))
    
    context = {
        'files': page_obj,
        'collections': collections,
        'current_collection': collection_filter,
        'search_query': search_query,
        'username': request.session.get('username'),
    }
    
    return render(request, 'dashboard/file_list.html', context)

@api_login_required
def file_upload(request):
    """Dosya yükleme görünümü"""
    print("Dosya yükleme sayfası açıldı")
    
    # Koleksiyon parametresini URL'den al
    collection_param = request.GET.get('collection')
    
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        
        # Koleksiyon listesini API'den al ve forma ekle
        collections = get_collections_from_api(request.session.get('api_token'))
        collection_names = [c['name'] for c in collections]
        form.fields['collection'].choices = [(None, 'Ana Dizin')] + [(name, name) for name in collection_names]
        
        if form.is_valid():
            uploaded_file = request.FILES['file']
            collection_name = form.cleaned_data.get('collection')
            
            print(f"Dosya yükleniyor: {uploaded_file.name}, Koleksiyon: {collection_name}")
            
            # API ile dosya yükleme
            result = api_upload_file(uploaded_file, collection_name, request.session.get('api_token'))
            print(f"API yanıtı: {result}")
            
            if result.get('success', False):
                messages.success(request, f"{result.get('name')} dosyası başarıyla yüklendi.")
                
                # Eğer bir koleksiyona yüklendiyse, o koleksiyona geri dön
                if collection_name:
                    # Koleksiyon indeksini bul
                    try:
                        collection_index = collection_names.index(collection_name) + 1
                        return redirect('dashboard:collection_detail', pk=collection_index)
                    except ValueError:
                        pass
                
                return redirect('dashboard:file_list')
            else:
                messages.error(request, f"Dosya yüklenirken bir hata oluştu: {result.get('error')}")
        else:
            print(f"Form geçerli değil: {form.errors}")
            messages.error(request, f"Form geçerli değil: {form.errors}")
    else:
        form = FileUploadForm()
        
        # Koleksiyon listesini API'den al
        collections = get_collections_from_api(request.session.get('api_token'))
        collection_names = [c['name'] for c in collections]
        form.fields['collection'].choices = [(None, 'Ana Dizin')] + [(name, name) for name in collection_names]
        
        # URL'den gelen koleksiyon parametresini ayarla
        if collection_param:
            try:
                form.initial['collection'] = collection_param
            except Exception as e:
                print(f"Koleksiyon parametresi ayarlanamadı: {str(e)}")
    
    context = {
        'form': form,
        'title': 'Dosya Yükle',
        'username': request.session.get('username'),
        'collection_param': collection_param,  # Template'e koleksiyon parametresini geç
    }
    
    return render(request, 'dashboard/file_upload.html', context)

@api_login_required
def bulk_upload(request):
    """Toplu dosya yükleme görünümü"""
    if request.method == 'POST':
        form = BulkUploadForm(request.POST)
        
        # Koleksiyon listesini API'den al ve forma ekle
        collections = get_collections_from_api(request.session.get('api_token'))
        collection_names = [c['name'] for c in collections]
        form.fields['collection'].choices = [(name, name) for name in collection_names]
        
        if form.is_valid():
            collection_name = form.cleaned_data['collection']
            files = request.FILES.getlist('files[]')
            
            if not files:
                messages.error(request, "Lütfen en az bir dosya seçin.")
                return redirect('dashboard:bulk_upload')
            
            # API ile toplu dosya yükleme
            result = api_bulk_upload(files, collection_name, request.session.get('api_token'))
            
            if result.get('success', False):
                total = result.get('total', 0)
                successful = result.get('successful', 0)
                failed = result.get('failed', 0)
                messages.success(
                    request, 
                    f"{successful}/{total} dosya başarıyla yüklendi. {failed} dosya başarısız."
                )
                return redirect('dashboard:collection_list')
            else:
                messages.error(request, f"Dosyalar yüklenirken bir hata oluştu: {result.get('error')}")
                print(f"Bulk upload hatası: {result}")
        else:
            messages.error(request, f"Form geçerli değil: {form.errors}")
    else:
        form = BulkUploadForm()
        # Koleksiyon listesini API'den al
        collections = get_collections_from_api(request.session.get('api_token'))
        collection_names = [c['name'] for c in collections]
        form.fields['collection'].choices = [(name, name) for name in collection_names]
    
    context = {
        'form': form,
        'title': 'Toplu Dosya Yükleme',
        'username': request.session.get('username'),
    }
    
    return render(request, 'dashboard/bulk_upload.html', context)

@api_login_required
def file_detail(request, pk):
    """Dosya detay görünümü"""
    # Dosyalar artık API'den geliyor, bu yüzden pk parametresi yerine
    # dosya yolunu kullanacağız
    
    # Tüm dosyaları tara
    cdn_data = scan_cdn_folder()
    files = cdn_data.get('files', [])
    
    # pk indeksine göre dosyayı bul
    try:
        file_info = files[int(pk) - 1]  # pk 1'den başlıyor varsayalım
    except (IndexError, ValueError):
        messages.error(request, "Dosya bulunamadı.")
        return redirect('dashboard:file_list')
    
    context = {
        'file': file_info,
        'pk': pk,  # pk değişkenini context'e ekle
        'username': request.session.get('username'),
    }
    
    return render(request, 'dashboard/file_detail.html', context)

@api_login_required
def file_edit(request, pk):
    """Dosya düzenleme görünümü"""
    # Dosyalar artık API'den geliyor, bu yüzden pk parametresi yerine
    # dosya yolunu kullanacağız
    
    # Tüm dosyaları tara
    cdn_data = scan_cdn_folder()
    files = cdn_data.get('files', [])
    
    # pk indeksine göre dosyayı bul
    try:
        file_info = files[int(pk) - 1]  # pk 1'den başlıyor varsayalım
    except (IndexError, ValueError):
        messages.error(request, "Dosya bulunamadı.")
        return redirect('dashboard:file_list')
    
    if request.method == 'POST':
        form = FileEditForm(request.POST)
        if form.is_valid():
            new_name = form.cleaned_data['name']
            new_collection = form.cleaned_data.get('collection')
            
            # Dosya adı değiştiyse, yeniden adlandır
            if new_name != file_info['name']:
                rename_result = rename_file(file_info['path'], new_name)
                if not rename_result['success']:
                    messages.error(request, f"Dosya adı değiştirilirken bir hata oluştu: {rename_result.get('error')}")
                    return redirect('dashboard:file_list')
                
                file_info['path'] = rename_result['path']
                file_info['name'] = os.path.basename(rename_result['path'])
            
            # Koleksiyon değiştiyse, dosyayı taşı
            current_collection = file_info.get('collection')
            if new_collection != current_collection:
                move_result = move_file(file_info['path'], new_collection)
                if not move_result['success']:
                    messages.error(request, f"Dosya taşınırken bir hata oluştu: {move_result.get('error')}")
                    return redirect('dashboard:file_list')
                
                file_info['path'] = move_result['path']
            
            messages.success(request, f"{file_info['name']} dosyası başarıyla güncellendi.")
            return redirect('dashboard:file_list')
    else:
        # Form için başlangıç değerlerini ayarla
        form = FileEditForm(initial={
            'name': file_info['name'],
            'collection': file_info.get('collection')
        })
    
    # Koleksiyon listesini API'den al
    collections = get_collections_from_api(request.session.get('api_token'))
    form.fields['collection'].choices = [(None, 'Ana Dizin')] + [(c, c) for c in collections]
    
    context = {
        'form': form,
        'file': file_info,
        'pk': pk,  # pk değişkenini context'e ekle
        'username': request.session.get('username'),
    }
    
    return render(request, 'dashboard/file_edit.html', context)

@api_login_required
def file_delete(request, pk):
    """Dosya silme görünümü"""
    # Dosyalar artık API'den geliyor, bu yüzden pk parametresi yerine
    # dosya yolunu kullanacağız
    
    # Tüm dosyaları tara
    cdn_data = scan_cdn_folder()
    files = cdn_data.get('files', [])
    
    # pk indeksine göre dosyayı bul
    try:
        file_info = files[int(pk) - 1]  # pk 1'den başlıyor varsayalım
    except (IndexError, ValueError):
        messages.error(request, "Dosya bulunamadı.")
        return redirect('dashboard:file_list')
    
    if request.method == 'POST':
        # API ile dosyayı sil
        file_path = os.path.relpath(file_info['path'], settings.CDN_FOLDER).replace("\\", "/")
        success = api_delete_file(file_path, request.session.get('api_token'))
        
        if success:
            messages.success(request, f"{file_info['name']} dosyası başarıyla silindi.")
        else:
            messages.error(request, "Dosya silinirken bir hata oluştu.")
        
        return redirect('dashboard:file_list')
    
    context = {
        'file': file_info,
        'pk': pk,  # pk değişkenini context'e ekle
        'username': request.session.get('username'),
    }
    
    return render(request, 'dashboard/file_confirm_delete.html', context)

@api_login_required
def sync_with_cdn(request):
    """CDN ile senkronizasyon görünümü (Flask API'ye POST atar)"""
    if request.method == 'POST':
        api_token = request.session.get('api_token')
        api_url = f"{settings.CDN_API_URL}/admin/sync_cdn_db"
        try:
            response = requests.post(api_url, headers={
                'Authorization': api_token,
                'Accept': 'application/json',
            })
            if response.status_code == 200:
                return JsonResponse(response.json())
            else:
                return JsonResponse({'status': 'error', 'message': response.text}, status=response.status_code)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Sadece POST istekleri desteklenir.'}, status=405)

@api_login_required
def api_collections(request):
    """API'den koleksiyonları al ve JSON olarak döndür"""
    collections = get_collections_from_api(request.session.get('api_token'))
    return JsonResponse({'collections': collections})

@api_login_required
def api_files(request):
    """API'den dosyaları al ve JSON olarak döndür"""
    collection = request.GET.get('collection')
    page = request.GET.get('page', 1, type=int)
    per_page = request.GET.get('per_page', 20, type=int)
    
    files = get_files_from_api(collection=collection, page=page, per_page=per_page)
    return JsonResponse(files)

@api_login_required
def proxy_image(request):
    """CDN API'den gelen görüntüleri proxy olarak sunar ve Authorization token'ını URL'de gönderir"""
    path = request.GET.get('path')
    width = request.GET.get('width')
    
    if not path:
        return HttpResponse("Path parameter is required", status=400)
    
    # API token'ını al
    token = request.session.get('api_token')
    if not token:
        return HttpResponse("Unauthorized", status=401)
    
    # CDN API'ye istek gönder
    # Docker içindeki URL'yi tarayıcıda çalışacak şekilde dönüştür
    url = convert_docker_url_to_browser_url(f"{settings.CDN_API_URL}/cdn/{path}")
    params = {'token': token}
    if width:
        params['width'] = width
    
    try:
        response = requests.get(
            url,
            params=params,
            stream=True
        )
        
        if response.status_code == 200:
            # Content-Type header'ını al
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            
            # Response oluştur
            django_response = HttpResponse(
                response.content,
                content_type=content_type
            )
            
            # Cache header'larını ekle
            django_response['Cache-Control'] = 'max-age=86400'  # 1 gün
            
            return django_response
        else:
            return HttpResponse(f"Image not found: {response.text}", status=response.status_code)
    except Exception as e:
        return HttpResponse(f"Error fetching image: {str(e)}", status=500)

@api_login_required
def api_delete_file_endpoint(request):
    """API endpoint to delete a file"""
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Only POST method is allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        file_path = data.get('path')
        
        if not file_path:
            return JsonResponse({"success": False, "message": "File path is required"}, status=400)
        
        # API ile dosyayı sil
        success = api_delete_file(file_path, request.session.get('api_token'))
        
        if success:
            return JsonResponse({"success": True, "message": "File deleted successfully"})
        else:
            return JsonResponse({"success": False, "message": "Failed to delete file"}, status=500)
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)
