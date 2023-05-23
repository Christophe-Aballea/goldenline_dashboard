import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

rayons =  ['DPH', 'Alimentaire', 'Textile', 'Multimedia']


def determine_chart_types(category, number_of_collections):
    chart_types = []
    if category == "":
        if number_of_collections <= 12:
            chart_types.append("stacked_bar_chart")
        else:
            chart_types.append("lines_chart")
        chart_types.append("pie_chart")
    else:
        if number_of_collections <= 12:
            chart_types.append("bar_chart")
        else:
            chart_types.append("line_chart")
    return chart_types


def line_chart(data, mode, category):
    title = f"Évolution du {mode} rayon {category}"
    fig = px.line(data, x='Date de collecte', y=f'{mode} {category}')
    fig.update_layout(xaxis_title='Date de collecte', yaxis_title='Euros')
    html_string = pio.to_html(fig, full_html=False)
    return html_string, title


def lines_chart(data, mode, category):
    title = f"Évolution des {mode} par rayon"
    values = [f"{mode} {rayon}" for rayon in rayons]
    fig = px.line(data, x='Date de collecte', y=values)
    fig.update_layout(xaxis_title='Date de collecte', yaxis_title='Euros')
    html_string = pio.to_html(fig, full_html=False).replace('"legend":{"title":{"text":"variable"}', '"legend":{"title":{"text":""}')
    return html_string, title


def bar_chart(data, mode, category):
    # TODO Régler problème d'affichage des valeurs intermédiaire axe des abscisses
    title = f"Évolution du {mode} / rayon {category}"
    fig = px.bar(x=data['Date de collecte'], y=data[f'{mode} {category}'])
    fig.update_layout(xaxis_title='Date de collecte', yaxis_title='Euros')
    html_string = pio.to_html(fig, full_html=False)
    return html_string, title


def stacked_bar_chart(data, mode, category):
    title = f"{mode} par rayon"
    values = [f"{mode} {rayon}" for rayon in rayons]
    fig = px.bar(data, x='Date de collecte', y=values)
    fig.update_layout(xaxis_title='Date de collecte', yaxis_title='Euros')
    html_string = pio.to_html(fig, full_html=False).replace('"legend":{"title":{"text":"variable"}', '"legend":{"title":{"text":""}')
    return html_string, title


def pie_chart(data, mode, category):
    start_date = data['Date de collecte'].min()
    end_date = data['Date de collecte'].max()
    title = f"Répartition du {mode} sur la période {start_date} / {end_date}"
    values = [data[f"{mode} {rayon}"].sum() for rayon in rayons]
    fig = px.pie(values=values, names=rayons)
    html_string = pio.to_html(fig, full_html=False)
    return html_string, title



def generate_graph(collectes, criteria):
    # Dictionnaire des fonctions générant les graphiques
    chart_functions = {"line_chart": line_chart,
                       "lines_chart": lines_chart,
                       "bar_chart": bar_chart,
                       "stacked_bar_chart": stacked_bar_chart,
                       "pie_chart": pie_chart}

    # Extraction des critères
    mode = criteria["mode"]
    if mode == "PM":
        mode = "Panier moyen"
    category = criteria["rayon"]
    number_of_collections = len(collectes)

    # Choix du (des) type(s) de graphiques à générer
    chart_types = determine_chart_types(category, number_of_collections)

    # Génération des graphiques et conversion en HTML 
    charts_html_strings = [chart_functions[func_name](collectes, mode, category) for func_name in chart_types]

    return charts_html_strings

