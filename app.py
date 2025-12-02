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
        div[data-testid="stImage"] img { border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

st.title("📸 Foto 3x4 Studio")
st.write("Alta resolução para impressão.")

# --- Estados ---
if 'rotation' not in st.session_state: st.session_state.rotation = 0
if 'last_file' not in st.session_state: st.session_state.last_file = None
if 'processed_image' not in st.session_state: st.session_state.processed_image = None

# --- Funções ---

def resize_for_display(image, max_width=500):
    """
    Cria uma cópia leve da imagem apenas para visualização na tela.
    Retorna a imagem redimensionada e o fator de escala.
    """
    w, h = image.size
    if w > max_width:
        ratio = max_width / w
        new_h = int(h * ratio)
        return image.resize((max_width, new_h), Image.Resampling.LANCZOS), ratio
    return image, 1.0

def process_high_res(original_img, crop_box, scale_factor):
    """
    Aplica o corte na imagem ORIGINAL (Alta Resolução) usando as coordenadas ajustadas.
    """
    # 1. Recuperar as coordenadas reais na imagem gigante
    # O crop_box vem da imagem pequena, então dividimos pelo scale_factor (ou multiplicamos pelo inverso)
    # Como scale_factor = width_pequena / width_original
    # Então width_original = width_pequena / scale_factor
    
    left = int(crop_box['left'] / scale_factor)
    top = int(crop_box['top'] / scale_factor)
    width = int(crop_box['width'] / scale_factor)
    height = int(crop_box['height'] / scale_factor)
    
    # 2. Cortar a imagem original gigante
    high_res_crop = original_img.crop((left, top, left + width, top + height))
    
    # 3. Remover fundo (IA)
    img_no_bg = remove(high_res_crop)
    
    # 4. Colocar fundo branco
    new_image = Image.new("RGBA", img_no_bg.size, "WHITE")
    new_image.paste(img_no_bg, (0, 0), img_no_bg)
    final_rgb = new_image.convert("RGB")
    
    # 5. Redimensionar para o padrão de impressão 300 DPI
    # Padrão 3x4cm a 300 DPI = 354 x 472 pixels.
    # Essa resolução garante impressão nítida no tamanho físico 3x4.
    return final_rgb.resize((354, 472), Image.Resampling.LANCZOS)

# --- UPLOAD ---
st.divider()
uploaded_file = st.file_uploader("📂 Carregue a foto original", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Resetar estados se mudar arquivo
    if st.session_state.last_file != uploaded_file.name:
        st.session_state.rotation = 0
        st.session_state.processed_image = None
        st.session_state.last_file = uploaded_file.name

    # Carregar Imagem Original (Mantemos ela na memória intacta)
    original_image = Image.open(uploaded_file)
    original_image = ImageOps.exif_transpose(original_image)
    
    # Aplicar rotação na original
    rotated_original = original_image.rotate(st.session_state.rotation, expand=True)
    
    # Criar versão de visualização (Leve) e pegar o fator de escala
    display_image, scale = resize_for_display(rotated_original, max_width=500)

    # --- EDIÇÃO ---
    st.divider()
    with st.container(border=True):
        st.markdown("**Ajuste o Enquadramento:**")
        
        # Botões de Giro
        c1, c2 = st.columns(2)
        with c1:
            if st.button("↺ Girar"):
                st.session_state.rotation += 90
                st.session_state.processed_image = None
                st.rerun()
        with c2:
            if st.button("Girar ↻"):
                st.session_state.rotation -= 90
                st.session_state.processed_image = None
                st.rerun()

        # O CROPPER mostra a imagem pequena, mas retorna as coordenadas (box)
        # return_type='box' é o segredo aqui!
        crop_box = st_cropper(
            display_image,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=(3, 4),
            return_type='box' 
        )
        
        if st.button("✨ Processar em Alta Qualidade", type="primary"):
            with st.spinner("Processando imagem em alta resolução..."):
                try:
                    # Enviamos a imagem ORIGINAL e as coordenadas para processar
                    result = process_high_res(rotated_original, crop_box, scale)
                    st.session_state.processed_image = result
                except Exception as e:
                    st.error(f"Erro ao processar: {e}")

    # --- RESULTADO ---
    if st.session_state.processed_image is not None:
        st.divider()
        st.markdown("#### ✅ Foto Pronta")
        
        col1, col2 = st.columns([1, 1.5], gap="medium")
        
        with col1:
            # Mostra preview
            st.image(st.session_state.processed_image, caption="Preview", use_container_width=True)
        
        with col2:
            st.success("Tratamento concluído!")
            st.info("Formato: 3x4 cm (300 DPI)\nFundo: Branco")
            
            buf = io.BytesIO()
            st.session_state.processed_image.save(buf, format="PNG", optimize=True)
            byte_im = buf.getvalue()

            st.download_button(
                label="📥 Baixar PNG para Impressão",
                data=byte_im,
                file_name="foto_3x4_hd.png",
                mime="image/png",
                type="primary"
            )
