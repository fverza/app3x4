import streamlit as st
from rembg import remove
from PIL import Image, ImageOps
import io
from streamlit_cropper import st_cropper

# Configuração da página
st.set_page_config(page_title="Criador de Foto 3x4", page_icon="📸", layout="wide")

st.title("📸 Gerador de Foto 3x4 Profissional")

# --- Lógica de Estado (Session State) ---
# Isso serve para o app "lembrar" a rotação atual
if 'rotation' not in st.session_state:
    st.session_state.rotation = 0
if 'last_file' not in st.session_state:
    st.session_state.last_file = None

def add_white_background(image_input):
    """Remove o fundo e insere um fundo branco"""
    img_no_bg = remove(image_input)
    new_image = Image.new("RGBA", img_no_bg.size, "WHITE")
    new_image.paste(img_no_bg, (0, 0), img_no_bg)
    return new_image.convert("RGB")

# --- Interface do Usuário ---

uploaded_file = st.file_uploader("Escolha uma imagem", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Verifica se o usuário trocou de arquivo para resetar a rotação
    if st.session_state.last_file != uploaded_file.id:
        st.session_state.rotation = 0
        st.session_state.last_file = uploaded_file.id

    # Carrega a imagem e corrige orientação EXIF (importante para fotos de celular)
    original_image = Image.open(uploaded_file)
    original_image = ImageOps.exif_transpose(original_image)
    
    # Aplica a rotação armazenada no estado
    # expand=True garante que a imagem não seja cortada ao girar
    rotated_image = original_image.rotate(st.session_state.rotation, expand=True)

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Ajuste e Corte")
        
        # --- Botões de Rotação ---
        col_rot1, col_rot2, col_rot3 = st.columns([1, 1, 2])
        with col_rot1:
            if st.button("↺ Girar Esq."):
                st.session_state.rotation += 90
                st.rerun() # Recarrega a página para aplicar o giro
        with col_rot2:
            if st.button("↻ Girar Dir."):
                st.session_state.rotation -= 90
                st.rerun()
        
        # --- Ferramenta de Corte ---
        # Agora passamos a 'rotated_image' para o cortador
        cropped_img = st_cropper(
            rotated_image,
            realtime_update=True,
            box_color='red',
            aspect_ratio=(3, 4),
            should_resize_image=True
        )
        
        st.caption("Use os botões para girar e a caixa vermelha para enquadrar.")
        process_btn = st.button("✂️ Recortar e Remover Fundo", type="primary")

    with col2:
        st.subheader("2. Resultado Final")
        
        if process_btn:
            if cropped_img:
                with st.spinner("Processando..."):
                    try:
                        # Processa a imagem
                        final_image = add_white_background(cropped_img)
                        
                        # Redimensiona para padrão 3x4cm (300 DPI)
                        final_image = final_image.resize((354, 472), Image.Resampling.LANCZOS)
                        
                        st.image(final_image, caption="Foto 3x4 Pronta", width=200)

                        # Preparar Download
                        buf = io.BytesIO()
                        final_image.save(buf, format="PNG")
                        byte_im = buf.getvalue()
                        
                        st.success("Pronto!")
                        
                        st.download_button(
                            label="📥 Baixar Imagem .PNG",
                            data=byte_im,
                            file_name="foto_3x4_final.png",
                            mime="image/png"
                        )
                    except Exception as e:
                        st.error(f"Erro: {e}")