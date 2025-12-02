import streamlit as st
from rembg import remove
from PIL import Image, ImageOps
import io
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
        /* Ajustes para abas */
        .stTabs [data-baseweb="tab-list"] { justify-content: center; }
    </style>
""", unsafe_allow_html=True)

st.title("📸 Foto 3x4 Studio")
st.write("Alta resolução para impressão.")

# --- Estados ---
if 'rotation' not in st.session_state: st.session_state.rotation = 0
if 'mirror' not in st.session_state: st.session_state.mirror = False
if 'last_file' not in st.session_state: st.session_state.last_file = None
if 'processed_image' not in st.session_state: st.session_state.processed_image = None

# --- Funções ---

def resize_for_display(image, max_width=500):
    """Cria cópia leve para visualização"""
    w, h = image.size
    if w > max_width:
        ratio = max_width / w
        new_h = int(h * ratio)
        return image.resize((max_width, new_h), Image.Resampling.LANCZOS), ratio
    return image, 1.0

def process_high_res(original_img, crop_box, scale_factor):
    """Aplica corte na imagem original e remove fundo"""
    left = int(crop_box['left'] / scale_factor)
    top = int(crop_box['top'] / scale_factor)
    width = int(crop_box['width'] / scale_factor)
    height = int(crop_box['height'] / scale_factor)
    
    high_res_crop = original_img.crop((left, top, left + width, top + height))
    
    img_no_bg = remove(high_res_crop)
    
    new_image = Image.new("RGBA", img_no_bg.size, "WHITE")
    new_image.paste(img_no_bg, (0, 0), img_no_bg)
    final_rgb = new_image.convert("RGB")
    
    # 3x4cm a 300 DPI = 354 x 472 pixels
    return final_rgb.resize((354, 472), Image.Resampling.LANCZOS)

# --- ÁREA DE INPUT (ABAS) ---
st.divider()

# Criação das abas
tab1, tab2 = st.tabs(["📂 Galeria (Upload)", "📸 Câmera"])

source_file = None
source_name = ""

with tab1:
    uploaded_file = st.file_uploader("Escolha uma imagem", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
    if uploaded_file:
        source_file = uploaded_file
        source_name = uploaded_file.name

with tab2:
    camera_file = st.camera_input("Tirar foto agora", label_visibility="collapsed")
    if camera_file:
        source_file = camera_file
        source_name = "camera_capture"

# --- LÓGICA DE PROCESSAMENTO ---

if source_file is not None:
    # Resetar se o arquivo mudou
    if st.session_state.last_file != source_name:
        st.session_state.rotation = 0
        st.session_state.mirror = False
        st.session_state.processed_image = None
        st.session_state.last_file = source_name

    # Carregar Imagem
    original_image = Image.open(source_file)
    original_image = ImageOps.exif_transpose(original_image)
    
    # Aplicar Transformações (Espelhamento e Rotação)
    # Importante: A ordem afeta o resultado. Geralmente espelha-se primeiro se for selfie.
    img_to_show = original_image
    
    if st.session_state.mirror:
        img_to_show = ImageOps.mirror(img_to_show)
        
    rotated_original = img_to_show.rotate(st.session_state.rotation, expand=True)
    
    # Redimensionar para visualização
    display_image, scale = resize_for_display(rotated_original, max_width=500)

    # --- EDIÇÃO ---
    st.divider()
    with st.container(border=True):
        st.markdown("**Ajuste o Enquadramento:**")
        
        # Botões de Controle (Agora com Espelhar)
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("↺ Esq."):
                st.session_state.rotation += 90
                st.session_state.processed_image = None
                st.rerun()
        with c2:
            # Botão útil para Câmera Frontal
            if st.button("↔ Espelhar"):
                st.session_state.mirror = not st.session_state.mirror
                st.session_state.processed_image = None
                st.rerun()
        with c3:
            if st.button("Dir. ↻"):
                st.session_state.rotation -= 90
                st.session_state.processed_image = None
                st.rerun()

        # Ferramenta de Corte
        crop_box = st_cropper(
            display_image,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=(3, 4),
            return_type='box' 
        )
        
        if st.button("✨ Processar Foto 3x4", type="primary"):
            with st.spinner("Removendo fundo em alta qualidade..."):
                try:
                    result = process_high_res(rotated_original, crop_box, scale)
                    st.session_state.processed_image = result
                except Exception as e:
                    st.error(f"Erro ao processar: {e}")

    # --- RESULTADO ---
    if st.session_state.processed_image is not None:
        st.divider()
        st.markdown("#### ✅ Resultado Final")
        
        col1, col2 = st.columns([1, 1.5], gap="medium")
        
        with col1:
            st.image(st.session_state.processed_image, caption="Preview", use_container_width=True)
        
        with col2:
            st.success("Pronto!")
            st.write("3x4 cm • 300 DPI")
            
            buf = io.BytesIO()
            st.session_state.processed_image.save(buf, format="PNG", optimize=True)
            byte_im = buf.getvalue()

            st.download_button(
                label="📥 Baixar PNG",
                data=byte_im,
                file_name="foto_3x4_studio.png",
                mime="image/png",
                type="primary"
            )
