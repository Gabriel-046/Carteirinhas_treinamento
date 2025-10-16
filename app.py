@st.cache_data
def gerar_carteirinha(nome, re_input, cargo, depto, unidade, treinamentos):
    background = Image.open(layout_path).convert("RGB")
    draw = ImageDraw.Draw(background)

    logo = Image.open(logo_path).resize((150, 150))
    background.paste(logo, (50, 50))

    try:
        font_colab = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
        font_trein = ImageFont.truetype("DejaVuSans.ttf", 15)
    except:
        font_colab = ImageFont.load_default()
        font_trein = ImageFont.load_default()

    text_x = 50
    text_y_start = 220
    line_height = 45

    draw.text((text_x, text_y_start), f"NOME: {nome}", font=font_colab, fill="black")
    draw.text((text_x, text_y_start + line_height), f"RE: {re_input}", font=font_colab, fill="black")
    draw.text((text_x, text_y_start + 2 * line_height), f"CARGO: {cargo}", font=font_colab, fill="black")
    draw.text((text_x, text_y_start + 3 * line_height), f"DEPARTAMENTO: {depto}", font=font_colab, fill="black")
    draw.text((text_x, text_y_start + 4 * line_height), f"UNIDADE: {unidade}", font=font_colab, fill="black")

    train_x = background.width // 2 + 30
    train_y_start = 60
    max_chars = 65

    draw.text((train_x, train_y_start), "TREINAMENTOS:", font=font_trein, fill="black")
    current_y = train_y_start + 40
    for treinamento in treinamentos:
        linhas = textwrap.wrap(treinamento, width=max_chars)
        for linha in linhas:
            draw.text((train_x + 20, current_y), f"- {linha}", font=font_trein, fill="black")
            current_y += 25

    output_path = "carteirinha_final.png"
    background.save(output_path)
    return output_path
