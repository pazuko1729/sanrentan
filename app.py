from flask import Flask, request, render_template, redirect, url_for, session
from flask_session import Session  # 追加
import random
import json

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# サーバーサイドセッションの設定
app.config['SESSION_TYPE'] = 'filesystem'  # ファイルシステムにセッションを保存
Session(app)

# Jinja2グローバル関数としてenumerateを追加
app.jinja_env.globals.update(enumerate=enumerate)
app.jinja_env.globals.update(len=len)

class SanrentanGame:
    def __init__(self, players, topics):
        self.players = players
        self.topics = topics
        self.scores = {player: 0 for player in players}
        self.rounds = len(players)
        self.current_round = 0
        self.current_player = None
        self.guess_index = 0
        self.guesses = {}
        self.previous_topic = None  # 追加: 前回のラウンドのお題を保持

    def start_game(self):
        # self.select_new_topic()
        topic, options = random.choice(list(self.topics.items()))
        self.topic = topic
        self.options = options
        self.select_random_parent()
    
    # def select_new_topic(self):
    #     available_topics = [t for t in self.topics.keys() if t != self.previous_topic]
    #     if not available_topics:  # 前回のお題以外がない場合、リセット
    #         available_topics = list(self.topics.keys())
    #     topic = random.choice(available_topics)
    #     self.previous_topic = topic  # 選んだお題を保存
    #     self.topic = topic
    #     self.options = self.topics[topic]

    def select_random_parent(self):
        self.current_player = random.choice(self.players)
        
    def next_round(self):
        if self.current_round < self.rounds:
            # self.select_new_topic()  # 新しいお題を選ぶ
            remaining_players = [p for p in self.players if p != self.current_player]
            self.current_player = random.choice(remaining_players)
            self.current_round += 1
            self.guess_index = 0
            self.guesses = {} #変更点
            return True
        else:
            return False

    def calculate_scores(self, correct_order, guesses):
        round_scores = {}
        for player, guess in guesses.items():
            score = self.evaluate_guess(correct_order, guess)
            self.scores[player] += score
            round_scores[player] = score
        return round_scores

    def evaluate_guess(self, correct_order, guess):
        correct_set = set(correct_order)
        guess_set = set(guess)

        if correct_order == guess:
            return 6  # サンレンタン
        elif correct_set == guess_set:
            return 4  # サンレンプク
        elif len(correct_set.intersection(guess_set)) == 2:
            correct_pos = sum(correct_order[i] == guess[i] for i in range(3))
            if correct_pos == 2:
                return 3  # ニレンタン
            else:
                return 2  # ニレンプク
        elif len(correct_set.intersection(guess_set)) == 1:
            return 1  # タン
        else:
            return 0

    def declare_winner(self):
        winner = max(self.scores, key=self.scores.get)
        return winner, self.scores

    def to_dict(self):
        return {
            'players': self.players,
            'topics': self.topics,
            'scores': self.scores,
            'rounds': self.rounds,
            'current_round': self.current_round,
            'topic': getattr(self, 'topic', None),
            'options': getattr(self, 'options', None),
            'current_player': getattr(self, 'current_player', None),
            'guess_index': self.guess_index,
            'guesses': self.guesses,
        }

    @staticmethod
    def from_dict(data):
        game = SanrentanGame(data['players'], data['topics'])
        game.scores = data['scores']
        game.rounds = data['rounds']
        game.current_round = data['current_round']
        game.topic = data.get('topic', None)
        game.options = data.get('options', None)
        game.current_player = data.get('current_player', None)
        game.guess_index = data.get('guess_index', 0)
        game.guesses = data.get('guesses', {})
        return game

def save_game_to_session(game):
    session['game'] = game.to_dict()

def load_game_from_session():
    return SanrentanGame.from_dict(session['game'])

@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')

@app.route('/rules', methods=['GET'])
def rules():
    return render_template('rules.html')

@app.route('/start_game', methods=['GET'])
def start_game():
    return redirect(url_for('player_count'))

@app.route('/player_count', methods=['GET', 'POST'])
def player_count():
    if request.method == 'POST':
        num_players = int(request.form['num_players'])
        session['num_players'] = num_players
        return redirect(url_for('player_names'))
    return render_template('player_count.html')

@app.route('/player_names', methods=['GET', 'POST'])
def player_names():
    num_players = session.get('num_players')
    if request.method == 'POST':
        players = [request.form[f'player_name_{i+1}'] for i in range(num_players)]
        topics = {"好きなおにぎりの具は？": ["うめ", "ツナマヨ", "唐揚げ", "おかか", "たらこ", "焼きおにぎり", "昆布"],
                  "過去にタイムスリップ出来たらどうする？": ["好きだった人に告白", "競馬や株で大勝", "同じ人生を味わう", 
                    "別の学校や職場に進む", "黒歴史をなかったことにする", "新たな趣味を始める", "大きい事件を未然に防ぐ"],
                  "腹立つ瞬間は？": ["レジの順番を抜かされる", "勝手に鞄を見られる", "したはずの料理の注文が通ってない",
                    "ファッションをいじられる", "お菓子を許可なく一口食べられる", "３日連続で雨", "コンビニに食べたいご飯がほとんどない"],
                  "住んでみたい町は？": ["ビルが立ち並ぶ大都会", "人情溢れる昔ながらの下町", "飲み屋の多い歓楽街",
                    "１日にバスが２本しか来ない田舎", "港がにぎわう漁師町", "古着屋やレコード屋が多いサブカル系", "風情溢れる温泉街"],
                  "お弁当のおかずでうれしいのは？": ["鶏のから揚げ", "卵焼き", "シュウマイ", "ミートボール", "鮭の塩焼き", "きんぴらごぼう", "梅干し"],
                  "一億円の代償として許せるのは？": ["一生、常温の飲み物しか飲めない", "一生、車に乗れない", "一生、三か月に一回引っ越し", 
                    "一生、公園に入れない", "一生、夜１２時~朝５時まで外に出られない", "一生、同じ色の服しか着られない", "一生、飲み会に参加できない"],
                  "言われたらうれしい誉め言葉は？": ["頭がいいね", "話し上手だね", "モテそうだね", "優しいね", "明るいね", "面白いね", "歌うまいね"],
                  "世界からなくなってもいいものは？": ["クイズ番組", "公園", "タクシー", "花火大会", "折り畳み傘", "デリバリー", "ゲームセンター"],
                  "恋人がしていたら嫌なことは？": ["異性のいる飲み会に参加", "隣で寝られないほどのいびき", "記念日を忘れる", 
                    "毎回、１０分以上遅刻する", "店員にため口で話す", "SNSでポエム投稿", "ゲームで台パン"],
                  "今からなれるならなりたい職業は？": ["スポーツ選手", "俳優", "科学者", "ストリーマー", "不労所得で年収1000万円", "政治家", "インフルエンサー"],
                  "生まれ変わったら何になりたい？": ["IQ200", "お金持ちに買われている猫", "渡り鳥", "クジラ", "大富豪の息子", "総理大臣", "自分"],
                  "宝くじで３億円当たったら？": ["車を買う", "一軒家を買う", "友達におごりまくる", "寄付する", "仕事を辞める", "今までと同じ生活を送る", "家族に半分あげる"],
                  "その作品の世界で暮らすなら？": ["ワンピース", "呪術廻戦", "鬼滅の刃", "サザエさん", "NARUTO", "鋼の錬金術師", "ハンターハンター"],
                  "余命１週間になったら何をする？": ["好きなものをたくさん食べる", "大事な人と過ごす", "仕事に没頭する", "早めに自殺する", "遠くに旅行する", "普段通りに過ごす", "犯罪を犯す"],
                  "知り合いに言われたら嫌なことは？": ["服がダサい", "育ちが悪そう", "友達少なそう", "頭悪くない？", "信用できない", "面白くない", "ゲームとかしてそう"],
                  "耐えられないのは？": ["３日間、知らない海外で暮らす", "３日間、カップラーメンしか食べない", "３日間、誰とも話さない", "３日間、スマホなしで過ごす", "３日間、労働時間が１２時間以上",
                    "３日間、睡眠時間が４時間", "３日間、山奥で暮らす"],
                  "初デートで行きたいのは？": ["テーマパーク", "水族館", "美術館", "日帰り旅行", "映画館", "お散歩", "居酒屋"],
                  "尊敬できるのは？": ["体を鍛えている", "知識や教養が豊富", "人脈が広い", "芸術面の才能がある", "盛り上げ上手", "会話が面白い", "仕事ができる"],
                  "見たいドキュメンタリー番組は？": ["強豪高校サッカー部の部室", "宇宙の形を知る物理学者～宇宙の果てとは？～", "世界一演技の下手な女優　リザ", 
                    "～外界と接触しない部族～　シタ族の実態", "開示請求で人生終了した男", "高校生たちの甘酸っぱい青春に密着", "～カリスマ詐欺師集団～　EDENが落ちぶれるまで"],
                  "副業を始めるとしたら？": ["家事代行", "フードデリバリー", "占い師", "家庭教師", "動画編集", "ハンドモデル", "インタビューの文字起こし"],
                  "落ち込んだ時の対処法は？": ["美味しいごはんを食べる", "カラオケで歌う", "友人・知人に相談する", "体を動かす", "自然に触れる", "とにかく寝る", "映画を見たり、本を読んだりする"],
                  "旅行でイラっとするのは？": ["自分が運転している助手席でいびきかいて寝てる", "旅行中ずっと天気が悪い", "レストランで自分の食べていメニューが売り切れ", 
                    "みんなが適当に置いたせいで自分の歯ブラシやタオルがわからない", "目当ての飲食店が定休日", "チェックアウトの時間になって準備を始める友達", "スマホの充電器を忘れた"],
                  "立ち直れないのは？": ["推しが活動休止した", "恋人から一日返信がない", "財布を無くした", "同窓会に呼ばれなかった", "旅行直前に体調不良", "お気に入りの服にソースをこぼした", "スマホを落として画面が割れた"]}
        game = SanrentanGame(players, topics)
        game.start_game()
        save_game_to_session(game)
        return redirect(url_for('choose_topic_or_random'))
    return render_template('player_names.html', num_players=num_players)

@app.route('/choose_topic_or_random', methods=['GET', 'POST'])
def choose_topic_or_random():
    game = load_game_from_session()
    if request.method == 'POST':
        choice = request.form['choice']
        if choice == 'random':
            game.start_game()  # ランダムにお題を選んでゲームを開始
            save_game_to_session(game)
            return redirect(url_for('parent_input'))
        elif choice == 'choose':
            return redirect(url_for('select_topic', page=1))
    return render_template('choose_topic_or_random.html')

@app.route('/select_topic/<int:page>', methods=['GET', 'POST'])
def select_topic(page=1):
    game = load_game_from_session()
    
    # お題を20個ずつ分割
    topics_per_page = 15
    topics_list = list(game.topics.keys())  # お題をリストに変換
    start = (page - 1) * topics_per_page
    end = page * topics_per_page
    topics_page = topics_list[start:end]
    
    # 最後のページかどうかを確認
    has_next = end < len(topics_list)
    has_previous = start > 0

    if request.method == 'POST':
        selected_topic = request.form['selected_topic']
        game.topic = selected_topic
        game.options = game.topics[selected_topic]
        save_game_to_session(game)
        return redirect(url_for('parent_input'))
    
    return render_template('select_topic.html', topics=topics_page, page=page, has_next=has_next, has_previous=has_previous)


@app.route('/parent_input', methods=['GET', 'POST'])
def parent_input():
    game = load_game_from_session()
    if request.method == 'POST':
        # 親が予測を入力した後、他のプレイヤーの予測画面へ移動
        correct_order = request.form.getlist('correct_order')
        session['correct_order'] = correct_order
        
        # 最初のプレイヤーに予測を入力させる（親は予測に参加しない）
        game.guess_index = 0
        save_game_to_session(game)

        return redirect(url_for('player_guess_input'))
    
    return render_template('parent_input.html', game=game)

@app.route('/player_guess_input', methods=['GET', 'POST'])
def player_guess_input():
    game = load_game_from_session()
    
    # 親を除外した残りのプレイヤーを取得
    remaining_players = [player for player in game.players if player != game.current_player]
    
    # もし、ゲームの予測順番がプレイヤー数 - 1 まで行ったら結果画面へ移動
    if game.guess_index >= len(remaining_players):
        return redirect(url_for('show_guesses'))
    
    current_guesser = remaining_players[game.guess_index]
    
    if request.method == 'POST':
        # プレイヤーの予測を受け取る
        guess = [
            request.form['guess_1'],
            request.form['guess_2'],
            request.form['guess_3']
        ]
        game.guesses[current_guesser] = guess
        
        # 次のプレイヤーに移動
        game.guess_index += 1
        save_game_to_session(game)

        # すべてのプレイヤー（親以外）の予測後、結果画面に移動
        if game.guess_index >= len(remaining_players):
            return redirect(url_for('show_guesses'))  # 最後のプレイヤーの予測後、結果画面に移動
        else:
            return redirect(url_for('player_guess_input'))  # 次のプレイヤーの予測画面へ移動

    return render_template('player_guess_input.html', game=game, current_guesser=current_guesser)

@app.route('/show_guesses', methods=['GET'])
def show_guesses():
    game = load_game_from_session()

    # 親を除外したプレイヤーリストを作成
    remaining_players = [player for player in game.players if player != game.current_player]
    
    # 親以外のプレイヤーの予測結果を取得
    guesses_with_options = {
        player: [(rank, game.options[int(rank) - 1]) for rank in game.guesses.get(player, [])]
        for player in remaining_players
    }

    return render_template('show_guesses.html', game=game, guesses_with_options=guesses_with_options)


@app.route('/show_results', methods=['GET', 'POST'])
def show_results():
    game = load_game_from_session()
    correct_order = session.get('correct_order')

    # 正解順位に対応する選択肢を取得
    correct_order_with_options = [(rank, game.options[int(rank) - 1]) for rank in correct_order]

    # 親を除いたプレイヤーの予測結果を取得
    remaining_players = [player for player in game.players if player != game.current_player]

    # 正解順位と各プレイヤーの予測順位を表示するための辞書を作成
    guesses_with_options = {
        player: [(rank, game.options[int(rank) - 1]) for rank in game.guesses.get(player, [])]
        for player in remaining_players
    }

    round_scores = game.calculate_scores(correct_order, game.guesses)

    # 親以外のプレイヤーの結果だけを表示
    save_game_to_session(game)

    return render_template('show_results.html',
                           game=game,
                           correct_order_with_options=correct_order_with_options,
                           round_scores=round_scores,
                           guesses_with_options=guesses_with_options)



@app.route('/continue_game', methods=['GET', 'POST'])
def continue_game():
    if request.method == 'POST':
        if 'yes' in request.form:
            game = load_game_from_session()
            if game.next_round():
                save_game_to_session(game)
                return redirect('/parent_input')
        return redirect(url_for('result'))
    return render_template('continue_game.html')

@app.route('/result', methods=['GET'])
def result():
    game = load_game_from_session()
    winner, scores = game.declare_winner()
    return render_template('result.html', winner=winner, scores=scores)

if __name__ == "__main__":
    app.run()