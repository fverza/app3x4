import streamlit as st
from rembg import remove
from PIL import Image, ImageOps
import io
import numpy as np
import cv2 # Biblioteca de visão computacional
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
        /* Abas centralizadas */
        .stTabs [data-baseweb="tab-list"] { justify-content: center; }
    </style>
""", unsafe_allow_html=True)

st.title("📸 Foto 3x4 Studio")
st.write("Detecção automática de rosto e alta resolução.")

# --- Estados ---
if 'rotation' not in st.session_state: st.session_state.rotation = 0
if 'mirror' not in st.session_state: st.session_state.mirror = False
if 'last_file' not in st.session_state: st.session_state.last_file = None
if 'processed_image' not in st.session_state: st.session_state.processed_image = None
if 'smart_crop_done' not in st.session_state: st.session_state.smart_crop_done = False
if 'pre_cropped_image' not in st.session_state: st.session_state.pre_cropped_image = None

# --- Funções ---

def smart_face_center(pil_image):
    """
    Usa OpenCV para detectar o rosto e cortar as laterais inúteis,
    centralizando a pessoa na imagem antes da edição manual.
    """
    # Converter PIL para OpenCV (numpy array)
    img_cv = np.array(pil_image)
    
    # Se tiver canal alpha (transparência), remove para não dar erro no cv2
    if img_cv.shape[2] == 4:
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGBA2RGB)
    else:
        # Se for RGB, OpenCV lê como RGB, mas para processar ok mantemos assim
        pass

    # Converter para escala de cinza para detecção
    gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)

    # Carregar o classificador de rosto pré-treinado do OpenCV
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # Detectar rostos
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    if len(faces) == 0:
        return pil_image # Se não achar rosto, retorna original

    # Pegar o maior rosto encontrado (caso tenha mais de um)
    x, y, w, h = max(faces, key=lambda b: b[2] * b[3])

    # Definir margens para incluir ombros e cabelo (Zoom Inteligente)
    height, width, _ = img_cv.shape
    
    # Queremos uma área que seja aprox 3x a largura do rosto para pegar os ombros
    # e um pouco acima da cabeça
    
    center_x = x + w // 2
    
    # Define a largura do novo corte (3x a largura do rosto ou largura total)
    new_width = min(width, int(w * 3.5))
    new_height = min(height, int(h * 4.5)) # Altura generosa para o busto

    # Calcular coordenadas do corte centralizado no rosto
    left = max(0, center_x - new_width // 2)
    top = max(0, y - int(h * 0.8)) # Pega um pouco acima da testa
    right = min(width, left + new_width)
    bottom = min(height, top + new_height)

    # Executa o corte "inteligente"
    pil_cropped = pil_image.crop((left, top, right, bottom))
    return pil_cropped

def resize_for_display(image, max_width=500):
    """Cria cópia leve para visualização"""
    w, h = image.size
    if w > max_width:
        ratio = max_width / w
        new_h = int(h * ratio)
        return image.resize((max_width, new_h), Image.Resampling.LANCZOS), ratio
    return image, 1.0

def process_high_res(image_to_process, crop_box, scale_factor):
    """Aplica corte final e remove fundo"""
    # Ajusta coordenadas baseadas na escala de visualização
    left = int(crop_box['left'] / scale_factor)
    top = int(crop_box['top'] / scale_factor)
    width = int(crop_box['width'] / scale_factor)
    height = int(crop_box['height'] / scale_factor)
    
    # Corta
    high_res_crop = image_to_process.crop((left, top, left + width, top + height))
    
    # Remove fundo
    img_no_bg = remove(high_res_crop)
    
    # Fundo branco
    new_image = Image.new("RGBA", img_no_bg.size, "WHITE")
    new_image.paste(img_no_bg, (0, 0), img_no_bg)
    final_rgb = new_image.convert("RGB")
    
    # 3x4cm a 300 DPI
    return final_rgb.resize((354, 472), Image.Resampling.LANCZOS)

# --- ÁREA DE INPUT ---
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

# --- LÓGICA PRINCIPAL ---

if source_file is not None:
    # Resetar estados se mudar o arquivo
    if st.session_state.last_file != source_name:
        st.session_state.rotation = 0
        st.session_state.mirror = False
        st.session_state.processed_image = None
        st.session_state.smart_crop_done = False # Reseta o zoom inteligente
        st.session_state.pre_cropped_image = None
        st.session_state.last_file = source_name

    # 1. Carregar imagem original
    original_image = Image.open(source_file)
    original_image = ImageOps.exif_transpose(original_image)
    
    # 2. Aplicar Espelho (Se necessário)
    if st.session_state.mirror:
        original_image = ImageOps.mirror(original_image)
        
    # 3. Aplicar Rotação
    rotated_original = original_image.rotate(st.session_state.rotation, expand=True)

    # 4. AUTO-CENTRALIZAÇÃO (SMART ZOOM)
    # Só fazemos isso uma vez por imagem para não ficar processando toda hora
    if not st.session_state.smart_crop_done:
        with st.spinner("Localizando rosto..."):
            st.session_state.pre_cropped_image = smart_face_center(rotated_original)
            st.session_state.smart_crop_done = True
    
    # Usamos a imagem pré-cortada (zoom no rosto) para o resto do processo
    working_image = st.session_state.pre_cropped_image
    
    # 5. Redimensionar para visualização no celular (max 500px largura)
    display_image, scale = resize_for_display(working_image, max_width=500)

    # --- EDIÇÃO ---
    st.divider()
    with st.container(border=True):
        st.markdown("**Ajuste o Enquadramento:**")
        
        # Botões
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("↺ Esq."):
                st.session_state.rotation += 90
                st.session_state.smart_crop_done = False # Refaz detecção na nova rotação
                st.rerun()
        with c2:
            if st.button("↔ Espelhar"):
                st.session_state.mirror = not st.session_state.mirror
                st.session_state.smart_crop_done = False # Refaz detecção
                st.rerun()
        with c3:
            if st.button("Dir. ↻"):
                st.session_state.rotation -= 90
                st.session_state.smart_crop_done = False
                st.rerun()

        # Ferramenta de Corte (Agora mostra a imagem JÁ com zoom no rosto)
        crop_box = st_cropper(
            display_image,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=(3, 4),
            return_type='box' 
        )
        
        if st.button("✨ Processar Foto 3x4", type="primary"):
            with st.spinner("Processando..."):
                try:
                    # Importante: Passamos a working_image (que é a pré-cortada de alta qualidade)
                    result = process_high_res(working_image, crop_box, scale)
                    st.session_state.processed_image = result
                except Exception as e:
                    st.error(f"Erro: {e}")

    # --- RESULTADO ---
    if st.session_state.processed_image is not None:
        st.divider()
        st.markdown("#### ✅ Resultado")
        
        col1, col2 = st.columns([1, 1.5], gap="medium")
        
        with col1:
            st.image(st.session_state.processed_image, caption="Final", use_container_width=True)
        
        with col2:
            st.success("Pronto!")
            
            buf = io.BytesIO()
            st.session_state.processed_image.save(buf, format="PNG", optimize=True)
            byte_im = buf.getvalue()

            st.download_button(
                label="📥 Baixar PNG",
                data=byte_im,
                file_name="foto_3x4.png",
                mime="image/png",
                type="primary"
            )
