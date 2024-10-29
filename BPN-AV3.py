import streamlit as st
import pandas as pd
from dbfread import DBF
import os
import plotly.express as px
import geopandas as gpd

#ESTILIZANDO!
st.set_page_config(layout='wide')
st.markdown(
    """
    <style>
    .reportview-container {
        background-color: black;  /* Cor de fundo preta */
    }
    .sidebar .sidebar-content {
        background-color: black;  /* Fundo da sidebar preta */
    }
    .stMetric, .stText {
        color: #89ffda;  /* Texto nas métricas e outros elementos */
    }
    h1, h2, h3, h4, h5, h6 {
        color: #89ffda;  /* Cor dos títulos */
    }
    .stButton {
        background-color: black;  /* Cor de fundo dos botões*/
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Caminho para o arquivo shapefile
shapefile_path = os.path.join(os.getcwd(), 'shapefile', 'PB_Municipios_2022.shp')  # Certifique-se de que o nome do arquivo está correto

# Carregar o shapefile
gdf = gpd.read_file(shapefile_path)

# Salvar como GeoJSON
# gdf.to_file('municipios_paraiba.geojson', driver='GeoJSON')



# Caminho relativo para o diretório onde estão os arquivos .csv
diretorio_csv = os.path.join(os.getcwd(), 'Dados_csv')

# Função para carregar dados diretamente dos arquivos CSV
def load_data(diretorio_csv):
    dataframes = []
    for arquivo in os.listdir(diretorio_csv):
        if arquivo.endswith('.csv'):
            caminho_completo = os.path.join(diretorio_csv, arquivo)
            try:
                # Definir os tipos de dados esperados para as colunas problemáticas
                dtypes = {
                    'IDADEMAE': 'float64',  # Exemplo, ajuste conforme necessário
                    'CODMUNNASC': 'str',     # Manter como string
                    'PESO': 'str'            # Manter como string antes da conversão
                }
                
                # Carregar cada arquivo CSV em um DataFrame e adicionar à lista
                df = pd.read_csv(caminho_completo, low_memory=False)
                dataframes.append(df)
            except Exception as e:
                st.error(f'Erro ao ler o arquivo {arquivo}: {e}')
    
    # Concatenar todos os DataFrames em um único DataFrame, se houver dados
    if dataframes:
        df_total = pd.concat(dataframes, ignore_index=True)
        return df_total
    else:
        st.warning('Nenhum arquivo .csv encontrado ou lido.')
        return None

# Carregar os dados CSV
df_total = load_data(diretorio_csv)



# Função para pré-processamento dos dados
def preprocess_data(df):
    try:
        # Converte a coluna DTNASC para datetime
        df['DTNASC'] = pd.to_datetime(df['DTNASC'], format='%d%m%Y', errors='coerce')
        
        # Converte a coluna PESO para string, substitui vírgulas por pontos e remove espaços
        df['PESO'] = df['PESO'].astype(str).str.replace(',', '.').str.strip()
        
        # Converter para float, forçando valores inválidos a serem NaN
        df['PESO'] = pd.to_numeric(df['PESO'], errors='coerce')
        
        # Converter a idade da mãe para numérico
        df['IDADEMAE'] = pd.to_numeric(df['IDADEMAE'], errors='coerce')

        # Garantir que CODMUNNASC seja uma string
        df['CODMUNNASC'] = df['CODMUNNASC'].fillna('').astype(str)

        # Filtragem para pesos abaixo de 2500 e códigos de município que começam com '25'
        df_baixo_peso = df[(df['PESO'] < 2500) & (df['PESO'] > 0) & (df['CODMUNNASC'].str.startswith('25'))].reset_index(drop=True)
        
        # Adiciona a coluna 'Ano' ao DataFrame df_baixo_peso
        df_baixo_peso['Ano'] = df_baixo_peso['DTNASC'].dt.year

        return df_baixo_peso
    except Exception as e:
        st.error(f"Erro durante o pré-processamento: {e}")
        return None

# Inicializa df_baixo_peso como None
df_baixo_peso = None

# Carregar e preparar a correspondência de nomes dos municípios
gdf_municipios = gpd.read_file('municipios_paraiba.geojson')
print(gdf_municipios.columns)
municipios_mapping = gdf_municipios[['CD_MUN', 'NM_MUN']].copy()
municipios_mapping.columns = ['CODMUNNASC', 'Nome_Municipio']

# Garantir que CODMUNNASC seja string para corresponder com os DataFrames
municipios_mapping['CODMUNNASC'] = municipios_mapping['CODMUNNASC'].astype(str)

# Mesclar o nome do município em df_baixo_peso e df_total
if df_total is not None:
    df_total = df_total.merge(municipios_mapping, on='CODMUNNASC', how='left')
    df_baixo_peso = preprocess_data(df_total)  # Chama a função de pré-processamento
    if df_baixo_peso is not None:
        df_baixo_peso = df_baixo_peso.merge(municipios_mapping, on='CODMUNNASC', how='left')

# Função para calcular métricas
def calculate_metrics(df_total, df_baixo_peso):
    if df_total is not None and df_baixo_peso is not None:
        soma_total_nascidos = len(df_total)
        soma_nascidos_abaixo_peso = len(df_baixo_peso)
        taxa_total_pb = (soma_nascidos_abaixo_peso / soma_total_nascidos) * 100
        media_idade_mae = df_total['IDADEMAE'].mean()

        return soma_nascidos_abaixo_peso, soma_total_nascidos, taxa_total_pb, media_idade_mae

    return None, None, None, None


# Função para visualização geral
def display_general_analysis(df_baixo_peso, df_total):
    # Criar um filtro deslizante para a idade da mãe
    idade_mae_min = int(df_total['IDADEMAE'].min())
    idade_mae_max = int(df_total['IDADEMAE'].max())
    
    # Usar uma chave única para o slider de idade da mãe
    idade_mae_selecionada = st.slider(
        "Selecione a faixa etária da mãe:",
        min_value=idade_mae_min,
        max_value=idade_mae_max,
        value=(idade_mae_min, idade_mae_max),  # Valores padrão
        key="idade_mae_slider_geral"  # Chave única
    )

    # Filtrar os dados de df_total e df_baixo_peso com base na idade da mãe
    df_filtrado_total = df_total[
        (df_total['IDADEMAE'] >= idade_mae_selecionada[0]) &
        (df_total['IDADEMAE'] <= idade_mae_selecionada[1])
    ]
    
    df_baixo_peso_filtrado = df_baixo_peso[
        (df_baixo_peso['IDADEMAE'] >= idade_mae_selecionada[0]) &
        (df_baixo_peso['IDADEMAE'] <= idade_mae_selecionada[1])
    ]

    # Calcular as métricas com base nos dados filtrados
    total_baixo_peso, total_nascidos, taxa_pb, media_idade_mae = calculate_metrics(df_filtrado_total, df_baixo_peso_filtrado)

    if total_baixo_peso is not None:
        # Criar 4 colunas para exibir as métricas
        col1, col2, col3, col4 = st.columns(4)

        # Adicionar cards nas colunas
        with col1:
            st.metric("Total de Nascimentos Abaixo do Peso", total_baixo_peso)

        with col2:
            st.metric("Total de Nascimentos", total_nascidos)

        with col3:
            st.metric("Nascimentos Abaixo do Peso (%)", f"{taxa_pb:.2f}")
        
        with col4:
            st.metric("Média da Idade das Mães", f"{media_idade_mae:.2f}")

        # Adicionar gráfico de evolução do número de nascimentos ao longo dos anos
        plot_nascimentos_por_ano(df_filtrado_total, df_baixo_peso_filtrado)


# Função Plot por
def plot_nascimentos_por_ano(df_total, df_baixo_peso):
    # Verificar se os dados estão disponíveis
    if df_total is not None:
        # Converter a coluna DTNASC para datetime se ainda não estiver
        df_total['DTNASC'] = pd.to_datetime(df_total['DTNASC'], format='%d%m%Y', errors='coerce')

        # Extrair o ano da data de nascimento
        df_total['Ano'] = df_total['DTNASC'].dt.year

        # Contar o número de nascimentos por ano
        nascimentos_por_ano = df_total.groupby('Ano').size().reset_index(name='Total_Nascimentos')
        nascimentos_baixo_peso_por_ano = df_baixo_peso.groupby('Ano').size().reset_index(name='Total_Baixo_Peso')

        # Mesclar os DataFrames para que ambos apareçam no gráfico
        df_combined = pd.merge(nascimentos_por_ano, nascimentos_baixo_peso_por_ano, on='Ano', how='outer')

        # Criar o gráfico de linha
        fig = px.line(df_combined, x='Ano', y=['Total_Nascimentos', 'Total_Baixo_Peso'],
                      title='Evolução do Número de Nascimentos ao Longo dos Anos',
                      labels={'value': 'Total', 'Ano': 'Ano'},
                      markers=True)

        # Exibir o gráfico
        st.plotly_chart(fig)
    else:
        st.warning('Nenhum dado disponível para plotar.')

# Função para visualização por município
def display_municipal_analysis(df_baixo_peso, df_total):

    # Calcular métricas por município
    metrics = df_baixo_peso['CODMUNNASC'].value_counts().reset_index()
    metrics.columns = ['CODMUNNASC', 'Nascimentos_Abaixo_Peso']

    total_nascimentos = df_total['CODMUNNASC'].value_counts().reset_index()
    total_nascimentos.columns = ['CODMUNNASC', 'Total_Nascimentos']

    # Mesclar os DataFrames
    merged = pd.merge(metrics, total_nascimentos, on='CODMUNNASC', how='outer')
    merged['Taxa_Abaixo_Peso'] = (merged['Nascimentos_Abaixo_Peso'] / merged['Total_Nascimentos']) * 100
    merged.fillna(0, inplace=True)  # Preencher NaN com 0

    # Criar um GeoDataFrame da Paraíba
    gdf_municipios = gpd.read_file('municipios_paraiba.geojson')  # Caminho do GeoJSON
    gdf_municipios['CODMUNNASC'] = gdf_municipios['CD_MUN'].astype(str)  # Usar a coluna correta

    # Mesclar o GeoDataFrame com as métricas
    gdf_merged = gdf_municipios.merge(merged, on='CODMUNNASC', how='left')

    # Criar o gráfico choropleth
    fig = px.choropleth(
        gdf_merged,
        geojson=gdf_merged.geometry,
        locations=gdf_merged.index,
        color='Taxa_Abaixo_Peso',  # Usar a taxa de nascimentos abaixo do peso
        hover_name='NM_MUN',
        hover_data=['Nascimentos_Abaixo_Peso', 'Total_Nascimentos'],
        color_continuous_scale=px.colors.sequential.YlOrRd,  # Amarelo para vermelho
        labels={'Taxa_Abaixo_Peso': 'Taxa de Nascimentos Abaixo do Peso (%)'}
    )

    # Ajustes para o gráfico
    fig.update_geos(
        fitbounds="locations",
        visible=False,
        bgcolor='rgba(0,0,0,0)')  #transparente
    
    # Ajusta o mapa
    fig.update_layout(
        height=600 ,
        title_text='Taxa de Nascimentos Abaixo do Peso por Município na Paraíba',
        paper_bgcolor='rgba(0,0,0,0)',  # Fundo do gráfico transparente
        plot_bgcolor='rgba(0,0,0,0)',    # Fundo da área de plotagem transparente
        coloraxis_colorbar=dict(title="Nascimentos Abaixo do Peso (%)")  # Título da barra de cores
    )

    # Exibir o gráfico
    st.plotly_chart(fig)  # Verifique se esta é a única chamada

# Função para visualização municipal comparativa
def display_municipal_analysis_comparative(df_baixo_peso, df_total):
    municipios = df_baixo_peso['Nome_Municipio'].unique().tolist()
    selected_municipios = st.multiselect("Selecione dois municípios para comparação", municipios)

    if len(selected_municipios) == 2:
        # Filtra os dados para os municípios selecionados
        df_municipio1 = df_baixo_peso[df_baixo_peso['Nome_Municipio'] == selected_municipios[0]]
        df_municipio2 = df_baixo_peso[df_baixo_peso['Nome_Municipio'] == selected_municipios[1]]

        # Criar um DataFrame com as métricas
        metricas = {
            'Municipio': [selected_municipios[0], selected_municipios[1]],
            'Nascimentos Abaixo do Peso': [len(df_municipio1), len(df_municipio2)],
            'Total de Nascimentos': [
                len(df_total[df_total['Nome_Municipio'] == selected_municipios[0]]),
                len(df_total[df_total['Nome_Municipio'] == selected_municipios[1]])
            ]
        }
        
        # Calcular a taxa de nascimento abaixo do peso
        taxa_nascimento_abaixo_peso = [
            (len(df_municipio1) / len(df_total[df_total['Nome_Municipio'] == selected_municipios[0]])) * 100,
            (len(df_municipio2) / len(df_total[df_total['Nome_Municipio'] == selected_municipios[1]])) * 100
        ]
        metricas['Taxa de Nascimento Abaixo do Peso (%)'] = taxa_nascimento_abaixo_peso
        
        df_metricas = pd.DataFrame(metricas)

        # Exibir métricas lado a lado
        col1, col2 = st.columns(2)

        with col1:
            st.subheader(selected_municipios[0])
            st.metric("Nascimentos Abaixo do Peso", df_metricas['Nascimentos Abaixo do Peso'][0])
            st.metric("Total de Nascimentos", df_metricas['Total de Nascimentos'][0])
            st.metric("Taxa de Nascimento Abaixo do Peso (%)", round(df_metricas['Taxa de Nascimento Abaixo do Peso (%)'][0], 2))

        with col2:
            st.subheader(selected_municipios[1])
            st.metric("Nascimentos Abaixo do Peso", df_metricas['Nascimentos Abaixo do Peso'][1])
            st.metric("Total de Nascimentos", df_metricas['Total de Nascimentos'][1])
            st.metric("Taxa de Nascimento Abaixo do Peso (%)", round(df_metricas['Taxa de Nascimento Abaixo do Peso (%)'][1], 2))

        # Criar um gráfico comparativo
        fig = px.bar(df_metricas, x='Municipio', 
                     y=['Nascimentos Abaixo do Peso', 'Total de Nascimentos'], 
                     title='Comparativo de Nascimentos Abaixo do Peso por Município')

        st.plotly_chart(fig)
    else:
        st.warning("Por favor, selecione exatamente dois municípios para comparação.")




st.title('Análise de Baixo Peso ao Nascer')

tab1, tab2, tab3 = st.tabs(["Página Inicial", "Visualização Geral", "Visualização Municipal"])

# Página Inicial
with tab1:
    st.header("Bem-vindo ao Projeto de Análise de Baixo Peso ao Nascer")
    st.write("""
    Este projeto visa analisar os dados sobre o baixo peso ao nascer (BPN) no estado da Paraíba, um problema significativo de saúde pública. O baixo peso ao nascer, definido como um peso inferior a 2500 gramas, está fortemente associado a maiores taxas de morbidade e mortalidade neonatal.

    ### Motivação
    A análise do BPN é crucial, pois ajuda a identificar fatores de risco que podem ser mitigados para melhorar os desfechos de saúde dos recém-nascidos. Vários elementos influenciam o BPN, como a saúde materna, o acesso a cuidados pré-natais e a idade gestacional. Observamos, por exemplo:
    
    - **Idade Gestacional**: Bebês nascidos antes de 37 semanas estão em risco elevado de mortalidade neonatal (Gaíva et al., 2014; Terzic & Heljic, 2011).
    - **Assistência Pré-Natal**: Consultas pré-natais insuficientes, especialmente menos de sete, aumentam consideravelmente o risco de BPN (Gaíva et al., 2014).
    - **Características Maternas**: Idade materna inferior a 20 anos, primiparidade e gravidezes múltiplas estão fortemente relacionadas ao BPN (Delaram, 2009).

    ### Insights
    Os resultados iniciais destacam os altos índices de mortalidade neonatal entre bebês com peso abaixo de 1500 gramas, onde estudos apontam uma taxa de mortalidade de até 29,85% entre recém-nascidos com peso extremamente baixo (Terzic & Heljic, 2011). Além disso, complicações como síndrome do desconforto respiratório e anomalias congênitas são prevalentes entre esses bebês (Nayeri et al., 2013; Gaíva et al., 2014). 
    
    Contudo, o desenvolvimento dos cuidados neonatais tem proporcionado melhores taxas de sobrevivência, mostrando a importância de investirmos em políticas e estratégias para redução do BPN.

    ### Objetivos
    O estudo aborda o tema em duas escalas:
    - **Geral**: Visão do Nordeste, contextualizando o estado da Paraíba dentro da região.
    - **Específico**: Foco detalhado na Paraíba, identificando disparidades na infraestrutura de saúde entre capitais e municípios do interior, além da necessidade de acompanhamento pré-natal adequado em cidades menores.

    ### Conclusão
    Observou-se uma disparidade significativa na infraestrutura de saúde entre grandes cidades, como João Pessoa e Campina Grande, e os municípios do interior. Muitas gestantes, sobretudo em áreas rurais, deslocam-se para essas grandes cidades em busca de melhores condições para o parto, refletindo desigualdades regionais que contribuem para o aumento do BPN. 

    ### Recomendações
    Para mitigar o BPN, é fundamental:
    - Expandir a infraestrutura de saúde nas cidades menores, promovendo o acesso ao pré-natal de qualidade.
    - Investir em capacitação profissional e equipamentos médicos nas áreas periféricas.
    - Criar centros regionais de referência para atender gravidezes de alto risco, reduzindo a necessidade de deslocamento para as grandes cidades.

    Campanhas educativas e intervenções preventivas sobre a importância do pré-natal também são essenciais para melhorar os desfechos de saúde neonatal, especialmente na Paraíba.
    """)  # Adicione sua descrição aqui

# Página de Visualização Geral do Estado
with tab2:
    st.header("Visualização Geral do Estado (Paraíba)")
    
    if df_total is not None:
        df_baixo_peso = preprocess_data(df_total)
        if df_baixo_peso is not None:
            display_municipal_analysis(df_baixo_peso, df_total)
            display_general_analysis(df_baixo_peso, df_total)
    else:
        st.error('Nenhum dado disponível para processamento.')

# Página de Visualização Municipal
# Página de Visualização Municipal
with tab3:
    st.header("Visualização Comparativo Municipal")

    if df_total is not None:
        df_baixo_peso = preprocess_data(df_total)
        if df_baixo_peso is not None:
            # Exibir visualização municipal comparativa
            display_municipal_analysis_comparative(df_baixo_peso,df_total)  # Passar apenas df_baixo_peso
