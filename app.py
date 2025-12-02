import streamlit as st
from rembg import remove
from PIL import Image, ImageOps
import io
import numpy as np
import cv2
from streamlit_cropper import st_cropper

# --- Configuração da Página ---
st.set_page_config(
    page_title="Foto 3x4 Studio", 
    page_icon="📸", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CSS Otimizado ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 3rem; }
        h1 { font-size: 1.5rem; text-align: center; margin-bottom: 0px; }
        p { font-size: 0.9rem; text-align: center; color: #555; }
        .stButton button { width: 100%; border-radius: 8px; }
        .stTabs [data-baseweb="tab-list"] { justify-content: center; }
    </style>
""", unsafe_allow_html=True)

st.title("📸 Foto 3x4 Studio")
st.write("Ajuste a posição e faça o recorte.")

# --- Estados ---
if 'rotation' not in st.session_state: st.session_state.rotation = 0
if 'mirror' not in st.session_state: st.session_state.mirror = False
if 'pan_x' not in st.session_state: st.session_state.pan_x = 0
if 'pan_y' not in st.session_state: st.session_state.pan_y = 0
if 'last_file' not in st.session_state: st.session_state.last_file = None
if 'processed_image' not in st.session_state: st.session_state.processed_image = None
if 'smart_crop_done' not in st.session_state: st.session_state.smart_crop_done = False
if 'pre_cropped_image' not in st.session_state: st.session_state.pre_cropped_image = None
if 'use_smart_crop' not in st.session_state: st.session_state.use_smart_crop = True

# --- Funções ---

def smart_face_center(pil_image):
    """Detecta rosto e centraliza com margem de segurança"""
    img_cv = np.array(pil_image)
    if img_cv.shape[2] == 4:
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGBA2RGB)
    
    gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))

    if len(faces) == 0:
        return pil_image

    x, y, w, h = max(faces, key=lambda b: b[2] * b[3])
    height_img, width_img, _ = img_cv.shape
    
    center_x = x + w // 2
    crop_w = int(w * 4.0) 
    crop_h = int(h * 6.0) 
    
    left = max(0, center_x - crop_w // 2)
    top = max(0, y - int(h * 1.5)) 
    
    right = min(width_img, left + crop_w)
    bottom = min(height_img, top + crop_h)

    if (right - left) < crop_w:
        left = max(0, right - crop_w)
    
    return pil_image.crop((left, top, right, bottom))

def shift_image(img, x_offset, y_offset):
    """Move a imagem dentro do quadro (Pan)"""
    if x_offset == 0 and y_offset == 0:
        return img
    
    # Cria fundo branco do mesmo tamanho
    bg = Image.new("RGB", img.size, (255, 255, 255))
    # Cola a imagem deslocada
    bg.paste(img, (x_offset, y_offset))
    return bg

def resize_for_display(image, max_width=500):
    w, h = image.size
    if w > max_width:
        ratio = max_width / w
        new_h = int(h * ratio)
        return image.resize((max_width, new_h), Image.Resampling.LANCZOS), ratio
    return image, 1.0

def process_high_res(image_to_process, crop_box, scale_factor):
    left = int(crop_box['left'] / scale_factor)
    top = int(crop_box['top'] / scale_factor)
    width = int(crop_box['width'] / scale_factor)
    height = int(crop_box['height'] / scale_factor)
    
    high_res_crop = image_to_process.crop((left, top, left + width, top + height))
    img_no_bg = remove(high_res_crop)
    new_image = Image.new("RGBA", img_no_bg.size, "WHITE")
    new_image.paste(img_no_bg, (0, 0), img_no_bg)
    return new_image.convert("RGB").resize((354, 472), Image.Resampling.LANCZOS)

# --- INPUT ---
st.divider()
tab1, tab2 = st.tabs(["📂 Galeria", "📸 Câmera"])

source_file = None
source_name = ""

with tab1:
    uploaded_file = st.file_uploader("Upload", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
    if uploaded_file:
        source_file = uploaded_file
        source_name = uploaded_file.name
with tab2:
    camera_file = st.camera_input("Foto", label_visibility="collapsed")
    if camera_file:
        source_file = camera_file
        source_name = "camera_capture"

# --- LÓGICA ---
if source_file is not None:
    if st.session_state.last_file != source_name:
        # Reset Total
        st.session_state.rotation = 0
        st.session_state.mirror = False
        st.session_state.pan_x = 0
        st.session_state.pan_y = 0
        st.session_state.processed_image = None
        st.session_state.smart_crop_done = False
        st.session_state.pre_cropped_image = None
        st.session_state.use_smart_crop = True
        st.session_state.last_file = source_name

    # 1. Carrega e prepara base
    original_image = Image.open(source_file)
    original_image = ImageOps.exif_transpose(original_image)
    if st.session_state.mirror:
        original_image = ImageOps.mirror(original_image)
    rotated_original = original_image.rotate(st.session_state.rotation, expand=True)

    # 2. Smart Crop (Zoom Automático)
    working_image = rotated_original
    if st.session_state.use_smart_crop:
        if not st.session_state.smart_crop_done:
            with st.spinner("Centralizando rosto..."):
                st.session_state.pre_cropped_image = smart_face_center(rotated_original)
                st.session_state.smart_crop_done = True
        if st.session_state.pre_cropped_image:
            working_image = st.session_state.pre_cropped_image

    # 3. APLICA MOVIMENTO (PAN) - NOVO!
    # Permite mover a imagem já recortada ou a original
    if st.session_state.pan_x != 0 or st.session_state.pan_y != 0:
        working_image = shift_image(working_image, st.session_state.pan_x, st.session_state.pan_y)

    # 4. Resize Display
    display_image, scale = resize_for_display(working_image, max_width=500)

    # --- CONTROLES E EDIÇÃO ---
    st.divider()
    
    with st.container(border=True):
        st.markdown("**1. Ajustes Gerais:**")
        c1, c2, c3 = st.columns(3)
        with c1: 
            if st.button("↺ Esq."): 
                st.session_state.rotation += 90
                st.session_state.smart_crop_done = False
                st.rerun()
        with c2: 
            if st.button("↔ Espelhar"): 
                st.session_state.mirror = not st.session_state.mirror
                st.session_state.smart_crop_done = False
                st.rerun()
        with c3: 
            if st.button("Dir. ↻"): 
                st.session_state.rotation -= 90
                st.session_state.smart_crop_done = False
                st.rerun()

        # --- NOVA ÁREA: MOVER A IMAGEM ---
        with st.expander("🛠️ Mover Imagem (Ajuste Fino)", expanded=False):
            st.caption("Se o rosto não ficou no centro, mova a imagem:")
            
            # Sliders para mover X e Y
            col_pan1, col_pan2 = st.columns(2)
            with col_pan1:
                st.session_state.pan_x = st.slider("↔️ Horizontal", -400, 400, st.session_state.pan_x, step=10)
            with col_pan2:
                st.session_state.pan_y = st.slider("↕️ Vertical", -200, 200, st.session_state.pan_y, step=10)
            
            if st.button("Zerar Posição"):
                st.session_state.pan_x = 0
                st.session_state.pan_y = 0
                st.rerun()

        # Botão Reset Zoom
        if st.session_state.use_smart_crop:
            if st.button("🔍 Cancelar Zoom Automático", type="secondary"):
                st.session_state.use_smart_crop = False
                st.session_state.smart_crop_done = False
                st.session_state.pan_x = 0
                st.session_state.pan_y = 0
                st.rerun()
        else:
            if st.button("🪄 Ativar Zoom Automático", type="secondary"):
                st.session_state.use_smart_crop = True
                st.rerun()

        st.markdown("**2. Recorte Final:**")
        crop_box = st_cropper(
            display_image,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=(3, 4),
            return_type='box' 
        )
        
        if st.button("✨ Processar Foto 3x4", type="primary"):
            with st.spinner("Gerando imagem final..."):
                try:
                    result = process_high_res(working_image, crop_box, scale)
                    st.session_state.processed_image = result
                except Exception as e:
                    st.error(f"Erro: {e}")

    # --- RESULTADO ---
    if st.session_state.processed_image is not None:
        st.divider()
        st.markdown("#### ✅ Resultado")
        col1, col2 = st.columns([1, 1.5])
        with col1:
            st.image(st.session_state.processed_image, caption="Final", use_container_width=True)
        with col2:
            st.success("Sucesso!")
            buf = io.BytesIO()
            st.session_state.processed_image.save(buf, format="PNG", optimize=True)
            byte_im = buf.getvalue()
            st.download_button("📥 Baixar PNG", data=byte_im, file_name="foto_3x4.png", mime="image/png", type="primary")

