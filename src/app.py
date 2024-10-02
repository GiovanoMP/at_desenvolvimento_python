import streamlit as st
from statsbombpy import sb
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import Pitch
from streamlit_option_menu import option_menu


# Configuração da página
st.set_page_config(layout="wide", page_title="Análises de Competições de Futebol")

# Funções auxiliares

@st.cache_data(show_spinner=False)
def load_competitions():
    """Carrega as competições da StatsBomb."""
    competitions = sb.competitions()
    return competitions

@st.cache_data(show_spinner=False)
def load_matches(competition_id, season_id):
    """Carrega as partidas de uma competição e temporada específicas."""
    matches = sb.matches(competition_id=competition_id, season_id=season_id)
    return matches

@st.cache_data(show_spinner=False)
def load_match_events(match_id):
    """Carrega os eventos de uma partida específica."""
    events = sb.events(match_id=match_id)
    return events

def calculate_match_stats(events, home_team, away_team):
    """Calcula estatísticas básicas da partida e identifica o vencedor."""
    total_passes = events[events['type'] == 'Pass'].shape[0]
    total_shots = events[events['type'] == 'Shot'].shape[0]
    total_goals_home = events[(events['team'] == home_team) & (events['shot_outcome'] == 'Goal')].shape[0]
    total_goals_away = events[(events['team'] == away_team) & (events['shot_outcome'] == 'Goal')].shape[0]
    total_goals = total_goals_home + total_goals_away  # Total de gols no jogo

    # Determinar o resultado
    if total_goals_home > total_goals_away:
        result = f"**{home_team} venceu** com {total_goals_home} gols."
    elif total_goals_away > total_goals_home:
        result = f"**{away_team} venceu** com {total_goals_away} gols."
    else:
        result = "**Empate**"

    # Exibir estatísticas 
    st.subheader("Resumo da Partida")
    col1, col2, col3 = st.columns(3)
    col1.metric(label="Total de Passes", value=total_passes)
    col2.metric(label="Total de Chutes", value=total_shots)
    col3.metric(label="Total de Gols", value=total_goals)

    st.subheader("Gols por Equipe")
    col1, col2 = st.columns(2)
    col1.metric(label=f"{home_team} Gols", value=total_goals_home)
    col2.metric(label=f"{away_team} Gols", value=total_goals_away)

    # Exibir resultado final
    st.subheader("Resultado Final")
    st.write(result)

def analyze_events(events):
    """Gera insights automáticos sobre a partida."""
    # Análise de passes
    top_passers = events[events['type'] == 'Pass']['player'].value_counts().head(3)
    st.write("**Top Passadores**:")
    for player, num_passes in top_passers.items():
        st.write(f"- {player}: {num_passes} passes")

    # Análise de chutes
    top_scorers = events[events['type'] == 'Shot']['player'].value_counts().head(3)
    st.write("**Top Finalizadores**:")
    for player, num_shots in top_scorers.items():
        st.write(f"- {player}: {num_shots} finalizações")

def plot_pass_map(events, team_name, player_name=None):
    """Gera o mapa de passes de uma equipe ou jogador."""
    passes = events[events['type'] == 'Pass']
    if player_name:
        passes = passes[passes['player'] == player_name]
    passes = passes[passes['team'] == team_name]

    if passes.empty:
        st.write("Nenhum dado de passes disponível para esta seleção.")
        return

    pitch = Pitch(pitch_type='statsbomb', pitch_color='#aabb97', line_color='white')
    fig, ax = pitch.draw(figsize=(10, 6))

    passes = passes.dropna(subset=['location', 'pass_end_location'])

    pitch.arrows(passes['location'].apply(lambda x: x[0]),
                 passes['location'].apply(lambda x: x[1]),
                 passes['pass_end_location'].apply(lambda x: x[0]),
                 passes['pass_end_location'].apply(lambda x: x[1]),
                 ax=ax, width=2, headwidth=10, color='blue', alpha=0.5)
    ax.set_title('Mapa de Passes', fontsize=14)
    st.pyplot(fig)

def plot_shot_map(events, team_name, player_name=None):
    """Gera o mapa de chutes de uma equipe ou jogador com xG."""
    shots = events[events['type'] == 'Shot']
    if player_name:
        shots = shots[shots['player'] == player_name]
    shots = shots[shots['team'] == team_name]

    if shots.empty:
        st.write("Nenhum dado de chutes disponível para esta seleção.")
        return

    shots = shots.dropna(subset=['location', 'shot_statsbomb_xg'])

    pitch = Pitch(pitch_type='statsbomb', pitch_color='#aabb97', line_color='white')
    fig, ax = pitch.draw(figsize=(10, 6))

    # Tamanho e cor dos pontos 
    sc = pitch.scatter(shots['location'].apply(lambda x: x[0]),
                       shots['location'].apply(lambda x: x[1]),
                       s=shots['shot_statsbomb_xg']*800 + 100,  # tamanho do círculo ajustado
                       c=shots['shot_statsbomb_xg'],            # cor do círculo
                       cmap='Reds', edgecolors='black', ax=ax, alpha=0.7)

    # Adicionar legendas
    ax.set_title('Mapa de Chutes', fontsize=14)
    sm = plt.cm.ScalarMappable(cmap='Reds', norm=plt.Normalize(vmin=shots['shot_statsbomb_xg'].min(), vmax=shots['shot_statsbomb_xg'].max()))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax)
    cbar.ax.set_ylabel('Expected Goals (xG)', rotation=270, labelpad=15)

    # Explicação adicional
    st.pyplot(fig)
    st.write("""
    **Interpretação do Mapa de Chutes:**

    - **Tamanho dos círculos**: Representa o valor do xG (probabilidade de gol). Quanto maior o círculo, maior a chance de gol naquela finalização.
    - **Cor dos círculos**: Tons mais escuros indicam maior xG.
    - **Localização**: Indica de onde os chutes foram realizados no campo.
    """)

def plot_heatmap(events, team_name, player_name=None):
    """Gera o mapa de calor de eventos de uma equipe ou jogador."""
    if player_name:
        events = events[events['player'] == player_name]
    events = events[events['team'] == team_name]

    # Remover entradas onde location e NaN
    events = events.dropna(subset=['location'])

    if events.empty:
        st.write("Nenhum dado disponível para esta seleção.")
        return

    pitch = Pitch(pitch_type='statsbomb', pitch_color='#aabb97', line_color='white')
    x = events['location'].apply(lambda loc: loc[0])
    y = events['location'].apply(lambda loc: loc[1])
    bin_statistic = pitch.bin_statistic(x, y, statistic='count', bins=(30, 30))
    fig, ax = pitch.draw(figsize=(10, 6))
    pcm = pitch.heatmap(bin_statistic, ax=ax, cmap='hot', edgecolors='white')
    cbar = plt.colorbar(pcm, ax=ax)
    cbar.ax.set_ylabel('Número de Eventos', rotation=270, labelpad=15)
    ax.set_title('Mapa de Calor', fontsize=14)
    st.pyplot(fig)
    st.write("""
    **Interpretação do Mapa de Calor:**

    - **Cores mais quentes (vermelho)**: Indicam áreas com maior concentração de eventos (ações) do jogador ou da equipe.
    - **Cores mais frias (amarelo a branco)**: Áreas com menor atividade.
    - **Utilidade**: Ajuda a identificar onde no campo o jogador ou equipe mais atuou, indicando padrões táticos.
    """)

def plot_event_timeline(events, home_team, away_team):
    """Gera uma linha do tempo dos eventos da partida com diferenciação por time."""
    events['timestamp'] = events['minute'] + events['second']/60

    event_types_english = ['Goal', 'Shot', 'Foul Committed', 'Yellow Card', 'Red Card']
    event_translation = {
        'Goal': 'Gol',
        'Shot': 'Chute',
        'Foul Committed': 'Falta Cometida',
        'Yellow Card': 'Cartão Amarelo',
        'Red Card': 'Cartão Vermelho'
    }
    event_types_portuguese = [event_translation[event] for event in event_types_english]

    events = events[events['type'].isin(event_types_english)]
    if events.empty:
        st.write("Nenhum evento relevante disponível para esta partida.")
        return

    # Mapear tipos de eventos para símbolos
    event_markers = {'Gol': 'o', 'Chute': 's', 'Falta Cometida': 'X', 'Cartão Amarelo': '^', 'Cartão Vermelho': 'v'}
    events['event_marker'] = events['type'].map(lambda x: event_markers[event_translation[x]])

    # Mapear times para cores
    team_colors = {home_team: 'blue', away_team: 'red'}
    events['team_color'] = events['team'].map(team_colors)

    fig, ax = plt.subplots(figsize=(12, 6))

    # Garantir que os eventos estejam ordenados
    events = events.sort_values('timestamp')

    for event_type in event_types_english:
        event_data = events[events['type'] == event_type]
        for team in [home_team, away_team]:
            team_data = event_data[event_data['team'] == team]
            if not team_data.empty:
                ax.scatter(team_data['timestamp'],
                           [event_translation[event_type]] * len(team_data),
                           c=team_colors[team],
                           marker=event_markers[event_translation[event_type]],
                           label=f"{event_translation[event_type]} - {team}",
                           edgecolors='black',
                           s=100)

    ax.set_xlabel('Tempo (minutos)')
    ax.set_ylabel('Tipo de Evento')
    ax.set_title('Linha do Tempo dos Eventos da Partida')

    # Remover duplicatas na legenda
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), bbox_to_anchor=(1.05, 1), loc='upper left')

    st.pyplot(fig)

    # Explicação dos eventos
    st.write("**Significado dos Eventos:**")
    st.write("""
    - **Gol**: Quando um jogador marca um gol.
    - **Chute**: Tentativa de marcar um gol, mas sem sucesso.
    - **Falta Cometida**: Quando um jogador comete uma infração contra um adversário.
    - **Cartão Amarelo**: Advertência dada a um jogador por conduta antidesportiva.
    - **Cartão Vermelho**: Expulsão do jogador por conduta grave ou segundo cartão amarelo.
    """)

    st.write("**Cores e Símbolos:**")
    st.write(f"""
    - **Cores dos Times:**
      - **{home_team}**: Azul
      - **{away_team}**: Vermelho
    - **Símbolos dos Eventos:**
      - **Gol**: Círculo (o)
      - **Chute**: Quadrado (s)
      - **Falta Cometida**: X
      - **Cartão Amarelo**: Triângulo para cima (^)
      - **Cartão Vermelho**: Triângulo para baixo (v)
    """)

def compare_players(events, team_name, player1, player2):
    """Compara estatísticas entre dois jogadores."""
    stats = ['Passes', 'Chutes', 'Gols', 'Assistências']
    player_stats = {}
    for player in [player1, player2]:
        player_events = events[(events['team'] == team_name) & (events['player'] == player)]
        passes = player_events[player_events['type'] == 'Pass'].shape[0]
        shots = player_events[player_events['type'] == 'Shot'].shape[0]
        goals = player_events[(player_events['type'] == 'Shot') & (player_events['shot_outcome'] == 'Goal')].shape[0]
        assists = player_events[player_events['pass_goal_assist'] == True].shape[0]
        player_stats[player] = [passes, shots, goals, assists]

    df = pd.DataFrame(player_stats, index=stats).T
    st.table(df)

def show_instructions():
    """Exibe as instruções de uso do dashboard."""
    st.title("Como Usar o Dashboard")
    st.write("""
        **Análises de Competições de Futebol** permite visualizar informações detalhadas de partidas de futebol, com base nos dados da StatsBomb.

        ### Funcionalidades:
        - **Estatísticas**: Veja um resumo das principais estatísticas da partida, incluindo total de passes, chutes e gols.
        - **Mapa de Passes**: Visualize a distribuição dos passes de um jogador ou da equipe.
        - **Mapa de Chutes**: Veja onde os chutes aconteceram durante o jogo, incluindo o xG.
        - **Mapa de Calor**: Analise a intensidade dos eventos em diferentes áreas do campo.
        - **Linha do Tempo de Eventos**: Entenda o fluxo do jogo ao longo do tempo, diferenciando os times.
        - **Comparação de Jogadores**: Compare estatísticas entre dois jogadores.
        - **Análise**: Obtenha insights automáticos sobre os principais passadores e finalizadores da partida.

        ### Passo a Passo:
        1. Selecione a competição, temporada e partida na barra lateral.
        2. Escolha uma equipe e um jogador para análise ou visualize a equipe como um todo.
        3. Navegue pelas abas para ver diferentes visualizações.
        4. Baixe os dados da partida em CSV se necessário.
    """)

# Layout

st.title("Análises de Competições de Futebol")

# Barra Lateral com menu
with st.sidebar:
    selected = option_menu(
        "Menu",
        ["Como Usar", "Estatísticas", "Mapa de Passes", "Mapa de Chutes", "Mapa de Calor", "Linha do Tempo", "Comparação de Jogadores", "Análise"],
        icons=['info', 'bar-chart', 'map', 'target', 'activity', 'clock', 'people', 'lightbulb'],
        menu_icon="cast",
        default_index=0
    )

# Filtros

competitions = load_competitions()
competition_name = st.sidebar.selectbox("Selecione a Competição", competitions['competition_name'].unique())
competition_id = competitions[competitions['competition_name'] == competition_name]['competition_id'].values[0]

filtered_seasons = competitions[competitions['competition_name'] == competition_name]
season_name = st.sidebar.selectbox("Selecione a Temporada", filtered_seasons['season_name'].unique())
season_id = filtered_seasons[filtered_seasons['season_name'] == season_name]['season_id'].values[0]

matches = load_matches(competition_id, season_id)
matches['match_name'] = matches['home_team'] + " vs " + matches['away_team']
match_name = st.sidebar.selectbox("Selecione a Partida", matches['match_name'].unique())
match_id = matches[matches['match_name'] == match_name]['match_id'].values[0]

# Verificação para evitar carregamento desnecessário
if 'loaded_match_id' not in st.session_state or st.session_state.loaded_match_id != match_id:
    with st.spinner('Carregando dados da partida...'):
        events = load_match_events(match_id)
        st.session_state.events = events
        st.session_state.loaded_match_id = match_id
else:
    events = st.session_state.events

home_team = matches[matches['match_name'] == match_name]['home_team'].values[0]
away_team = matches[matches['match_name'] == match_name]['away_team'].values[0]
teams = [home_team, away_team]
team_name = st.sidebar.selectbox("Selecione a Equipe para Análise", teams)

players = events[(events['team'] == team_name)]['player'].dropna().unique()
player_options = ["Todos os Jogadores"] + list(players)
player_name = st.sidebar.selectbox("Selecione o Jogador para Análise", player_options)
if player_name == "Todos os Jogadores":
    player_name = None

# Conteúdo Principal

if selected == "Como Usar":
    show_instructions()

elif selected == "Estatísticas":
    st.header(f"Análise da Partida: {match_name}")
    st.write(f"**Competição**: {competition_name}")
    st.write(f"**Temporada**: {season_name}")
    st.write("Nesta seção, você pode visualizar as estatísticas gerais da partida.")
    calculate_match_stats(events, home_team, away_team)
    st.subheader("Eventos da Partida")
    num_events = st.slider("Selecione o número de eventos para visualizar", min_value=5, max_value=50, value=10)
    st.dataframe(events[['minute', 'second', 'team', 'player', 'type', 'location']].head(num_events))

elif selected == "Mapa de Passes":
    st.subheader(f"Mapa de Passes de {'Todos os Jogadores' if not player_name else player_name} - {team_name}")
    st.write("Este mapa mostra a origem e o destino dos passes realizados, ajudando a entender a distribuição das jogadas.")
    plot_pass_map(events, team_name, player_name)

elif selected == "Mapa de Chutes":
    st.subheader(f"Mapa de Chutes de {'Todos os Jogadores' if not player_name else player_name} - {team_name}")
    st.write("Este mapa indica onde os chutes ocorreram e a qualidade das chances através do xG (Expected Goals).")
    plot_shot_map(events, team_name, player_name)

elif selected == "Mapa de Calor":
    st.subheader(f"Mapa de Calor de Eventos de {'Todos os Jogadores' if not player_name else player_name} - {team_name}")
    st.write("O mapa de calor ilustra as áreas do campo onde ocorreram mais ações, indicando a intensidade das jogadas.")
    plot_heatmap(events, team_name, player_name)

elif selected == "Linha do Tempo":
    st.subheader("Linha do Tempo dos Eventos da Partida")
    st.write("Visualize o momento em que os principais eventos ocorreram ao longo da partida, diferenciando cada time.")
    plot_event_timeline(events, home_team, away_team)

elif selected == "Comparação de Jogadores":
    st.subheader("Comparação entre Jogadores")
    st.write("Compare estatísticas chave entre dois jogadores da mesma equipe.")
    player1 = st.selectbox("Selecione o Primeiro Jogador", players, key='player1')
    player2 = st.selectbox("Selecione o Segundo Jogador", players, key='player2')
    if player1 and player2:
        compare_players(events, team_name, player1, player2)

elif selected == "Análise":
    st.subheader("Análise dos Eventos")
    st.write("Obtenha insights sobre os jogadores que mais se destacaram na partida.")
    analyze_events(events)

# Download de Dados
st.sidebar.subheader("Download")
csv = events.to_csv(index=False)
st.sidebar.download_button(
    label="Baixar eventos da partida em CSV",
    data=csv,
    file_name=f'{match_name}_events.csv',
    mime='text/csv',
)
