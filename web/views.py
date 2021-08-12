#!/usr/bin/python
# -*- coding: latin-1 -*-

import random, json

from django.shortcuts import render
from django.shortcuts import redirect
from django.template import loader
from django.http import HttpResponse
from django.db import transaction
from django.core import serializers

from core.models import *

ROUNDS = 3
RIGHT_ANSWER_MULTIPLIER = 15
RIGHT_CHALLENGE_ANSWER_MULTIPLIER = 30
WRONG_CHALLENGE_ANSWER_MULTIPLIER = 10
MAX_CHALLENGE_ANSWERS = 2

def render(request, context, template):
    template = loader.get_template('web/' + template)
    return template.render(context, request)

def http_render(request, context, template):
    return HttpResponse(render(request, context, template))

def menu(request):
    try:
        match = _recovery_match(request)
        return play_game(request)
    except:
        pass

    return http_render(request, {}, 'menu.html')

def new_game(request):
    _clear_match(request)
    return http_render(request, {}, 'setup.html')

def setup_game(request):
    try:
        n_teams = int(request.POST['teams'])
        normal_questions = list(Question.objects.filter(style='N'));
        challenge_questions = list(Question.objects.filter(style='C'));

        #Não tenho questẽes suficientes pra brincar
        if len(normal_questions) < (n_teams * ROUNDS) or len(challenge_questions) < ROUNDS:
            return menu(request)

        #Salvando a partida
        match = Match()
        match.save()
        request.session['game'] = match.id
        request.session.modified = True

        teams = []

        #Salvando os times
        for i in range(n_teams):
            name = request.POST['team'+str(i+1)]
            team = Team()
            team.match = match
            team.name = name if len(name) > 0 else 'Grupo ' + str(i+1)
            team.save()
            teams.append(team)

        #Sorteando as questões normais
        for r in range(ROUNDS):
            for t in range(n_teams):
                matchQuestion = MatchQuestion()
                matchQuestion.match = match
                matchQuestion.team = teams[t]
                matchQuestion.question = normal_questions.pop(random.randint(0, len(normal_questions)-1))
                matchQuestion.shift = r+1
                matchQuestion.save()

        #Sorteando as questões desafio
        for r in range(ROUNDS):
            matchQuestion = MatchQuestion()
            matchQuestion.match = match
            matchQuestion.question = challenge_questions.pop(random.randint(0, len(challenge_questions)-1))
            matchQuestion.shift = r+1
            matchQuestion.save()

        return redirect('/game/play')
    except:
        return menu(request)

def stop_game(request):
    _clear_match(request)
    return menu(request)

def play_game(request):
    try:
        context = _play_game(request)
    except:
        _clear_match(request)
        return menu(request)

    return http_render(request, context, 'play.html')

@transaction.atomic
def answer_game(request):
    try:
        match_question_id = int(request.POST['match_question'])
        alternative_id = int(request.POST['alternative'])
        shift = int(request.POST['shift'])
        team_id = int(request.POST['team'])

        match_question = MatchQuestion.objects.get(id=match_question_id)
        team = Team.objects.get(id=team_id)
        question = match_question.question

        if question.style == 'C':
            answer = Answer()
            answer.is_correct = (alternative_id == 1)
        else:
            answer = Answer.objects.get(id=alternative_id)

        match_question.right_answer = answer.is_correct

        #Calculando a pontuação com base no tipo de questão
        if answer.is_correct:
            if question.style == 'C':
                team.points += (shift * RIGHT_CHALLENGE_ANSWER_MULTIPLIER)

                del request.session['challenge']
                request.session.modified = True
            else:
                team.points += (shift * RIGHT_ANSWER_MULTIPLIER)
            team.save()
        elif question.style == 'C':
            match_question.right_answer = None

            teams = Team.objects.filter(match=match_question.match)
            for other_team in teams:
                if other_team.id != team.id:
                    other_team.points += (shift * WRONG_CHALLENGE_ANSWER_MULTIPLIER)
                    other_team.save()

            #Agora sorteando novo time
            challenge = _recovery_challenge(request)
            selected_teams = []
            challenge_answers = 0

            for team_challenge in challenge['teams']:
                if team_challenge['id'] == team.id:
                    team_challenge['status'] = 'W'
                    challenge_answers += 1
                elif team_challenge['status'] == 'C':
                    selected_teams.append(team_challenge)
                elif team_challenge['status'] == 'W':
                    challenge_answers += 1

            if len(selected_teams) > 0 and challenge_answers < MAX_CHALLENGE_ANSWERS:
                team_sorted = random.choice(selected_teams)
                team_sorted['status'] = 'S'

                match_question.team = Team.objects.get(id=team_sorted['id'])

                request.session['challenge'] = challenge
                request.session.modified = True
            else:
                match_question.right_answer = False

                del request.session['challenge']
                request.session.modified = True

        match_question.save()

        context = _play_game(request)
        content = render(request, context, 'game_over.html' if context['game_over'] else 'play_content.html')

        data_content = '{"show_dialog": false}' if question.style == 'C' else '{"show_dialog": true,"right_answer": '+str(match_question.right_answer).lower()+',"team_name": "'+team.name+'"}'

        return HttpResponse(json.dumps({
                "data": data_content, "html": content}),
            content_type="application/json")
    except:
        _clear_match(request)
        return menu(request)

def sort_challenge(request):
    try:
        match_question_id = int(request.POST['match_question'])
        shift = int(request.POST['shift'])
        selected_teams_ids = str(request.POST['selected_teams']).rstrip(',').split(',') if len(request.POST['selected_teams']) > 0 else []

        if len(selected_teams_ids) > 0:
            challenge = _recovery_challenge(request)
            challenge['sorted'] = True
            selected_teams = []

            for team in challenge['teams']:
                if str(team['id']) in selected_teams_ids:
                    team['status'] = 'C'
                    selected_teams.append(team)

            team_sorted = random.choice(selected_teams)
            team_sorted['status'] = 'S'

            match_question = MatchQuestion.objects.get(id=match_question_id)
            match_question.team = Team.objects.get(id=team_sorted['id'])
            match_question.save()

            request.session['challenge'] = challenge
            request.session.modified = True
        else:
            match_question = MatchQuestion.objects.get(id=match_question_id)
            match_question.right_answer = False
            match_question.save()

            del request.session['challenge']
            request.session.modified = True

        context = _play_game(request)
        content = render(request, context, 'game_over.html' if context['game_over'] else 'play_content.html')

        return HttpResponse(json.dumps({
                "html": content}),
            content_type="application/json")
    except:
        _clear_match(request)
        return menu(request)

def _game_over(request):
    context = {}
    match = _recovery_match(request)

    teams = list(_recovery_teams(match, '-points'))
    context['teams'] = teams
    context['game_over'] = True
    tie = False
    no_winner = False

    if len(teams) > 1 and teams[0].points == teams[1].points:
        if teams[0].points > 0:
            tie = True
        else:
            no_winner = True

    context['winner'] = teams[0].name
    context['no_winner'] = no_winner
    context['tie'] = tie

    return context

def _play_game(request):
    context = {}
    context['game_over'] = False

    match = _recovery_match(request)

    #Jogo começando agora galerinha
    if match.shift == 0:
        match.shift = 1
        match.save()

    match_questions = MatchQuestion.objects.filter(match=match, shift=match.shift)
    next_question = _next_question(match_questions)

    while next_question is None:
        #Jogo acabou agora galerinha
        if match.shift >= ROUNDS:
            return _game_over(request)
        #Indo para o próximo round
        else:
            match.shift += 1
            match.save()
            match_questions = MatchQuestion.objects.filter(match=match, shift=match.shift)
            next_question = _next_question(match_questions)

    context['match_question'] = next_question
    context['answers'] = _recovery_answers(next_question)
    context['shift'] = match.shift
    context['teams'] = list(_recovery_teams(match, '-points'))

    #Estamos em um desafio...
    if next_question.question.style == 'C':
        challenge = _recovery_challenge(request)

        #Preparando os times
        if challenge['teams'] is None:
            challenge['teams'] = []
            for team in list(_recovery_teams(match, 'id')):
                challenge['teams'].append({"id":team.id, "name":team.name, "status": 'N'})
            challenge['sorted'] = False

        context['challenge'] = challenge
        request.session['challenge'] = challenge
        request.session.modified = True

    return context

def _next_question(match_questions):
    challenges = []
    next_question = None

    for match_question in match_questions:
        if match_question.right_answer is None:
            if match_question.question.style == 'C':
                challenges.append(match_question)
            else:
                next_question = match_question
                break

    if len(challenges) == 0:
        challenges.append(None)

    return next_question if next_question is not None else challenges[0]

def _recovery_match(request):
    return Match.objects.get(id=int(request.session.get('game', None)))

def _recovery_challenge(request):
    return request.session.get('challenge', {'teams': None, 'sorted': False})

def _recovery_answers(match_question):
    answers_list = []
    answers = Answer.objects.filter(question=match_question.question)
    descriptor = 'a)'

    for answer in answers:
        answers_list.append((descriptor, answer))
        descriptor = chr(ord(descriptor[0])+1) + ')'

    return answers_list

def _recovery_teams(match, order):
     return Team.objects.filter(match=match).order_by(order)

def _clear_match(request):
    try:
        match = Match.objects.get(id=int(request.session.pop('game')))
        match.delete()

        del request.session['challenge']
        request.session.modified = True
    except:
        pass
