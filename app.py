import streamlit as st
from rembg import remove
from PIL import Image, ImageOps
import io
from streamlit_cropper import st_cropper

# --- Configuração da Página ---
st.set_page_config(
    page_title="Foto 3x4 Studio", 
    page_icon="📸", 
    layout="centered", # 'centered' fica melhor em celular e foca a atenção no PC
    initial_sidebar_state="collapsed"
)

# --- CSS Personalizado para Visual Mobile/PC ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        h1 {
            text-align: center;
            color: #333;
        }
        p {
            text-align: center;
            color: #666;
        }
        .stButton button {
            width: 100%; /* Botões ocupam largura total da coluna */
        }
    </style>
""", unsafe_allow_html=True)

# --- Título e Cabeçalho ---
st.title("📸 Foto 3x4 Studio")
st.write("Transforme suas selfies em fotos de documento profissionais em segundos.")

# --- Lógica de Estado (Session State) ---
if 'rotation' not in st.session_state:
    st.session_state.rotation = 0
if 'last_file' not in st.session_state:
    st.session_state.last_file = None
if 'processed_image' not in st.session_state:
    st.session_state.processed_image = None

def process_final_image(image_input):
    """Remove o fundo, adiciona branco e redimensiona"""
    img_no_bg = remove(image_input)
    new_image = Image.new("RGBA", img_no_bg.size, "WHITE")
    new_image.paste(img_no_bg, (0, 0), img_no_bg)
    final_rgb = new_image.convert("RGB")
    # Redimensiona para padrão 3x4cm (300 DPI) -> 354x472 pixels
    return final_rgb.resize((354, 472), Image.Resampling.LANCZOS)

# --- PASSO 1: UPLOAD ---
st.divider()
uploaded_file = st.file_uploader("📂 1. Carregue sua foto", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Resetar rotação se mudar o arquivo
    if st.session_state.last_file != uploaded_file.name:
        st.session_state.rotation = 0
        st.session_state.processed_image = None # Limpa resultado anterior
        st.session_state.last_file = uploaded_file.name

    # Carregar imagem
    original_image = Image.open(uploaded_file)
    original_image = ImageOps.exif_transpose(original_image)
    rotated_image = original_image.rotate(st.session_state.rotation, expand=True)

    # --- PASSO 2: EDIÇÃO (Container) ---
    st.divider()
    st.markdown("#### ✂️ 2. Ajuste o enquadramento")
    
    with st.container(border=True):
        # Controles de Rotação
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                if st.button("↺ Esq."):
                    st.session_state.rotation += 90
                    st.session_state.processed_image = None
                    st.rerun()
            with col_r2:
                if st.button("Dir. ↻"):
                    st.session_state.rotation -= 90
                    st.session_state.processed_image = None
                    st.rerun()

        # Ferramenta de Corte
        # box_color='red' destaca bem. aspect_ratio fixo garante o 3x4.
        cropped_img = st_cropper(
            rotated_image,
            realtime_update=True,
            box_color='#FF0000',
            aspect_ratio=(3, 4),
            should_resize_image=True
        )

        st.info("💡 Dica: Arraste os cantos vermelhos para ajustar o rosto e ombros.")
        
        # Botão de Processar Grande
        if st.button("✨ Processar Foto e Remover Fundo", type="primary"):
            with st.spinner("A IA está trabalhando..."):
                try:
                    result = process_final_image(cropped_img)
                    st.session_state.processed_image = result
                except Exception as e:
                    st.error(f"Erro: {e}")

    # --- PASSO 3: RESULTADO (Só aparece se tiver processado) ---
    if st.session_state.processed_image is not None:
        st.divider()
        st.markdown("#### ✅ 3. Resultado Final")
        
        with st.container(border=True):
            col_res1, col_res2 = st.columns([1, 1])
            
            with col_res1:
                # Mostra a imagem centralizada
                st.image(st.session_state.processed_image, caption="Padrão Documento", width=177) # Metade de 354px para visualização
            
            with col_res2:
                st.success("Sua foto está pronta!")
                st.write("Tamanho: 3x4 cm")
                st.write("Fundo: Branco")
                
                # Preparar buffer
                buf = io.BytesIO()
                st.session_state.processed_image.save(buf, format="PNG")
                byte_im = buf.getvalue()

                st.download_button(
                    label="📥 Baixar Imagem (PNG)",
                    data=byte_im,
                    file_name="foto_3x4_final.png",
                    mime="image/png",
                    type="primary"
                )
