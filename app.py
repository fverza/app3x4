import streamlit as st
from rembg import remove
from PIL import Image
import io
from streamlit_cropper import st_cropper

# Configuração da página
st.set_page_config(page_title="Criador de Foto 3x4", page_icon="📸", layout="wide")

st.title("📸 Gerador de Foto 3x4 Profissional")
st.markdown("""
**Passo 1:** Carregue a foto.  
**Passo 2:** Ajuste a caixa vermelha para enquadrar o rosto e ombros (proporção 3x4 fixa).  
**Passo 3:** Clique em Processar para remover o fundo.
""")

def add_white_background(image_input):
    """
    Remove o fundo e insere um fundo branco
    """
    # 1. Remover o fundo
    img_no_bg = remove(image_input)

    # 2. Criar fundo branco
    new_image = Image.new("RGBA", img_no_bg.size, "WHITE")
    new_image.paste(img_no_bg, (0, 0), img_no_bg)
    
    return new_image.convert("RGB")

# --- Interface do Usuário ---

uploaded_file = st.file_uploader("Escolha uma imagem", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    original_image = Image.open(uploaded_file)
    
    # Cria duas colunas: Esquerda (Corte) e Direita (Resultado)
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Ajuste o Corte")
        # Configuração do cortador (Cropper)
        # aspect_ratio=(3, 4) trava a caixa no formato documento
        cropped_img = st_cropper(
            original_image,
            realtime_update=True,
            box_color='red',
            aspect_ratio=(3, 4),
            should_resize_image=True # Redimensiona visualmente se a imagem for gigante
        )
        
        st.caption("Arraste os cantos da caixa vermelha para enquadrar.")
        
        # Botão de processamento fica aqui
        process_btn = st.button("✂️ Recortar e Remover Fundo", type="primary")

    with col2:
        st.subheader("2. Resultado Final")
        
        if process_btn:
            if cropped_img:
                with st.spinner("Processando imagem... (Isso pode levar alguns segundos)"):
                    try:
                        # Processa a imagem recortada
                        final_image = add_white_background(cropped_img)
                        
                        # Mostra o resultado
                        st.image(final_image, caption="Foto 3x4 Pronta", use_container_width=True) # use_container_width é o novo use_column_width

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
                        st.error(f"Erro ao processar: {e}")
            else:
                st.warning("Aguardando definição do corte...")