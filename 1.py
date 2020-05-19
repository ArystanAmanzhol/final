import random
import pika
import pygame
import time
from pygame import mixer
import json
import uuid
from threading import Thread
from enum import Enum
pygame.init()

bullet_shot_sound=pygame.mixer.Sound('bullet_shot.wav')
explosion_sound=pygame.mixer.Sound('explosion_sound.wav')
edaaa = pygame.mixer.Sound('kahoot1.wav')
mixer.music.load('background.mp3')
mixer.music.play(-1)

# MULTIPLAYER WINDOW( BIG )

width = 1000

# SINGLE AND MULTIPLAYER WINDOW( SMALL)

width_2 = 800
height = 600

screen = pygame.display.set_mode((width, height))

# colors
color_BLACK=(0, 0, 0)
color_WHITE=(255, 255, 255)
color_GREEN=(54, 64, 55)
color_RED=(255, 0, 0)
color_BROWN=(71, 40, 21)


# INFO ABOUT SERVER
IP = '34.254.177.17'
PORT = 5672
VIRTUAL_HOST = 'dar-tanks'
USERNAME = 'dar-tanks'
PASSWORD = '5orPLExUYnyVYZg48caMpX'

printing_type = pygame.font.SysFont('System', 32)
printing_type1 = pygame.font.SysFont("Comic Sans MS", 80)
printing_type2 = pygame.font.SysFont("Times New Roman", 40)
printing_type3 = pygame.font.SysFont("Times New Roman", 20)
printing_type4 = pygame.font.SysFont("Comic Sans MS", 26)

class TankRpcClient:

    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=IP,
                port=PORT,
                virtual_host=VIRTUAL_HOST,
                credentials=pika.PlainCredentials(
                    username=USERNAME,
                    password=PASSWORD
                )
            )
        )

        self.channel = self.connection.channel()
        queue = self.channel.queue_declare(queue='',
                                           auto_delete=True,
                                           exclusive=True)
        self.callback_queue = queue.method.queue
        self.channel.queue_bind(
            exchange='X:routing.topic',
            queue=self.callback_queue)

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)

        self.response = None
        self.corr_id = None
        self.token = None
        self.tank_id = None
        self.room_id = None

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = json.loads(body)
            print(self.response)

    def call(self, key, message={}):

        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='X:routing.topic',
            routing_key=key,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=json.dumps(message)
        )
        while self.response is None:
            self.connection.process_data_events()

    def check_server_status(self):
        self.call('tank.request.healthcheck')
        if self.response['status'] == '200':
            return True
        return False

    def obtain_token(self, room_id):
        message = {
            'roomId': room_id
        }
        self.call('tank.request.register', message)
        if 'token' in self.response:
            self.token = self.response['token']
            self.tank_id = self.response['tankId']
            self.room_id = self.response['roomId']
            return True
        return False

    def turn_tank(self, token, direction):
        message = {
            'token': token,
            'direction': direction
        }
        self.call('tank.request.turn', message)

    def shot(self, token):
        message = {
            'token': token
        }
        self.call('tank.request.fire', message)


class TankConsumerClient(Thread):

    def __init__(self, room_id):
        super().__init__()
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=IP,
                port=PORT,
                virtual_host=VIRTUAL_HOST,
                credentials=pika.PlainCredentials(
                    username=USERNAME,
                    password=PASSWORD
                )
            )
        )
        self.channel = self.connection.channel()
        queue = self.channel.queue_declare(queue='',
                                           auto_delete=True,
                                           exclusive=True
                                           )
        event_listener = queue.method.queue
        self.channel.queue_bind(exchange='X:routing.topic',
                                queue=event_listener,
                                routing_key='event.state.'+room_id)
        self.channel.basic_consume(
            queue=event_listener,
            on_message_callback=self.on_response,
            auto_ack=True
        )
        self.response = None

    def on_response(self, ch, method, props, body):
        self.response = json.loads(body)
        print(self.response)

    def run(self):
        self.channel.start_consuming()

UP = 'UP'
DOWN = 'DOWN'
LEFT = 'LEFT'
RIGHT = 'RIGHT'

MOVE_KEY = {
    pygame.K_w: UP,
    pygame.K_a: LEFT,
    pygame.K_s: DOWN,
    pygame.K_d: RIGHT
}


def start_online_game():
    client = TankRpcClient()

    client.check_server_status()
    client.obtain_token('room-10')

    event_collect = TankConsumerClient('room-10')

    event_collect.start()
    screen = pygame.display.set_mode((1300, 800))

    def blit_text(txt, x, y, FontSize, color):
        font = pygame.font.Font('freesansbold.ttf', FontSize)
        text = font.render(txt, 1, color)
        place = text.get_rect(center=(x, y))
        screen.blit(text, place)

    def draw_tank(x, y, width, height, direction, color_tank):
        tank_center = (x + width // 2, y + height // 2)

        pygame.draw.rect(screen, color_tank, (x, y, width, height), 6)
        pygame.draw.circle(screen, color_tank, tank_center, width // 2,4)


        if direction == 'RIGHT':
            pygame.draw.line(screen, color_tank,
                             (tank_center[0] + width // 2, tank_center[1]), (x + width + width // 2, y + height // 2), 4)
        if direction == 'LEFT':
            pygame.draw.line(screen, color_tank,
                             (tank_center[0] - width // 2, tank_center[1]), (x - width // 2, y + height // 2), 4)
        if direction == 'UP':
            pygame.draw.line(screen, color_tank,
                             (tank_center[0], tank_center[1] - width // 2), (x + width // 2, y - height // 2), 4)
        if direction == 'DOWN':
            pygame.draw.line(screen, color_tank,
                             (tank_center[0], tank_center[1] + width // 2), (x + width // 2, y + height + height // 2), 4)

    def draw_bullet(x, y, width, height, color_bullet):
        pygame.draw.rect(
            screen, color_bullet,
            (x, y, width, height)
        )

    game = True

    while game:
        screen.fill((0, 0, 0))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game = False

                if event.key in MOVE_KEY:
                    client.turn_tank(client.token, MOVE_KEY[event.key])

                if event.key == pygame.K_SPACE:
                    client.shot(client.token)
                    bullet_shot_sound.play()

                if event.key == pygame.K_ESCAPE:
                    game = False
                    main_menu()

        tanks = event_collect.response['gameField']['tanks']
        rem_time = event_collect.response['remainingTime']
        bullets = event_collect.response['gameField']['bullets']

        try:
            for tank in tanks:
                if client.tank_id == tank['id']:
                    draw_tank(tank['x'], tank['y'], tank['width'],tank['height'], tank['direction'], (35,187,17))
                else:
                    draw_tank(tank['x'], tank['y'], tank['width'],tank['height'], tank['direction'], (254,169,34))
        except:
            pass

        pygame.draw.rect(screen, (5, 105, 116), (949, 0, 289, 789))

        blit_text("Remaining Time: {}".format(rem_time), 1149, 729, 23, (255, 255, 255))
        number_of_tanks = len(tanks) - 1
        f = number_of_tanks
        counter = 0
        try:
            blit_text("My Tank          Health           Score", 1149, 29, 13, (255, 255, 255))
            blit_text("Enemy Tanks       Health           Score", 1149, 79, 15, (255, 255, 255))
            for tank in tanks:
                if client.tank_id == tank['id']:
                    blit_text(tank['id'] + "           " + str(tank['health']) + "               " + str(tank['score']), 1140, 50, 17, (34, 188, 16))
                else:
                    blit_text(
                        tank['id'] + "             " + str(tank['health']) + "                 " + str(tank['score']), 1149, 100 + (20 * counter), 17, (254, 169, 34))
                    counter += 1
                    if f == 0:
                        counter = 0
                        f = number_of_tanks
                    f -= 1
        except:
            pass

        try:
            for bullet in bullets:
                if client.tank_id == bullet['owner']:
                    draw_bullet(bullet['x'], bullet['y'], bullet['width'], bullet['height'], (34, 186, 16))
                else:
                    draw_bullet(bullet['x'], bullet['y'], bullet['width'], bullet['height'], (254, 169, 34))
        except:
            pass

        pygame.display.flip()

    pygame.quit()
    client.connection.close()
    event_collect.connection.close()


class Direction(Enum):
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4

class Tank:

    def __init__(self, x, y, speed, color, d_right=pygame.K_RIGHT, d_left=pygame.K_LEFT, d_up=pygame.K_UP,
                 d_down=pygame.K_DOWN, d_pull=pygame.K_RETURN):
        self.x = x
        self.y = y
        self.score = 3
        self.speed = 2
        self.color = color
        self.width = 30
        self.direction = Direction.RIGHT

        self.KEY = {d_right: Direction.RIGHT, d_left: Direction.LEFT,
                    d_up: Direction.UP, d_down: Direction.DOWN}

        self.KEYPULL = d_pull

    def draw(self):
        tank_center = (self.x + int(self.width / 2), self.y + int(self.width / 2))

        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.width), 2)

        pygame.draw.circle(screen, self.color, tank_center, int(self.width / 3))

        if self.direction == Direction.RIGHT:
            pygame.draw.line(screen, self.color, tank_center, (self.x + self.width + int(self.width / 2), self.y + int(self.width / 2)), 4)

        if self.direction == Direction.LEFT:
            pygame.draw.line(screen, self.color, tank_center, (self.x - int(self.width / 2), self.y + int(self.width / 2)), 4)

        if self.direction == Direction.UP:
            pygame.draw.line(screen, self.color, tank_center,
                             (self.x + int(self.width / 2), self.y - int(self.width / 2)), 4)

        if self.direction == Direction.DOWN:
            pygame.draw.line(screen, self.color, tank_center, (self.x + int(self.width / 2), self.y + self.width + int(self.width / 2)), 4)

    def change_direction(self, direction):
        self.direction = direction

    def move(self):
        if self.direction == Direction.LEFT:
            self.x -= self.speed
        if self.direction == Direction.RIGHT:
            self.x += self.speed
        if self.direction == Direction.UP:
            self.y -= self.speed
        if self.direction == Direction.DOWN:
            self.y += self.speed

        if self.x > width_2-40:
            self.x = 0 - self.width
        if self.x < 0 - self.width:
            self.x = width_2-40
        if self.y > height:
            self.y = 0 - self.width
        if self.y < 0 - self.width:
            self.y = height

        self.draw()


class Wall:
    def __init__(self):
        self.x = random.randint(0, 499)
        self.y = random.randint(0, 399)
        self.height = 40
        self.width = 40
        self.status = True

    def draw(self):
        wall = pygame.image.load('wall.png')
        screen.blit(wall, (self.x, self.y))


class Food:
    def __init__(self):
        self.x = random.randint(50, 600)
        self.y = random.randint(100, 600)
        self.status = True

    def draw(self):
        if self.status:
            foood = pygame.image.load('food.png')
            screen.blit(foood, (self.x, self.y))


class Pulya:
    def __init__(self, x=0, y=0, color=(0, 0, 0), direction=Direction.LEFT, speed=10):
        self.x = x
        self.y = y
        self.color = color
        self.speed = speed
        self.direction = direction
        self.status = True
        self.distance = 0
        self.radius = 7

    def move(self):
        if self.direction == Direction.LEFT:
            self.x -= self.speed

        if self.direction == Direction.RIGHT:
            self.x += self.speed

        if self.direction == Direction.UP:
            self.y -= self.speed

        if self.direction == Direction.DOWN:
            self.y += self.speed

        if self.distance > (2 * width):
            self.status = False

        self.distance += 1

        if self.x > 800:
            self.status = False

        self.draw()

    def draw(self):
        if self.status:
            pygame.draw.circle(screen, self.color, (self.x, self.y), self.radius)


def give_coordinates(tank):
    if tank.direction == Direction.RIGHT:
        x = tank.x + tank.width + int(tank.width / 2)
        y = tank.y + int(tank.width / 2)

    if tank.direction == Direction.LEFT:
        x = tank.x - int(tank.width / 2)
        y = tank.y + int(tank.width / 2)

    if tank.direction == Direction.UP:
        x = tank.x + int(tank.width / 2)
        y = tank.y - int(tank.width / 2)

    if tank.direction == Direction.DOWN:
        x = tank.x + int(tank.width / 2)
        y = tank.y + tank.width + int(tank.width / 2)

    p = Pulya(x, y, tank.color, tank.direction)
    pulya.append(p)


def collision():

    for p in pulya:

        for tank in tanks:

            if (tank.x + tank.width + p.radius > p.x > tank.x - p.radius) and ( (tank.y + tank.width + p.radius > p.y > tank.y - p.radius)) and p.status == True:
                explosion_sound.play()
                p.color = (0, 0, 0)
                tank.score -= 1

                p.status = False

                tank.x = random.randint(40, width - 70)
                tank.y = random.randint(40, height - 70)

            if tanks[0].score == 0:
                font1 = pygame.font.SysFont('System', 60)
                text = font1.render("Game Over :( BROWN tank won", 1, color_BROWN)
                place = text.get_rect(center=(400, 300))
                screen.blit(text, place)
                tank0.speed = 0
                tank1.speed = 0

            if tanks[1].score == 0:
                font2 = pygame.font.SysFont('System', 60)
                text = font2.render("Game Over :( BLACK tank won", 1, color_BLACK)
                place = text.get_rect(center=(400, 300))
                screen.blit(text, place)
                tank0.speed = 0
                tank1.speed = 0

    for p in pulya:
        for wall in walls:
            if (wall.x + wall.width + p.radius > p.x > wall.x - p.radius) and (
                    wall.y + wall.width + p.radius > p.y > wall.y - p.radius) and p.status == True:
                explosion_sound.play()
                p.color = (0, 0, 0)
                p.status = False

                wall.x = random.randint(0, width - 350)
                wall.y = random.randint(0, height - 30)

    for wall in walls:
        for tank in tanks:
            left_x1 = wall.x
            left_x2 = tank.x

            right_x1 = wall.x + wall.width
            right_x2 = tank.x + tank.width

            top_y1 = wall.y
            top_y2 = tank.y

            bottom_y1 = wall.y + wall.height
            bottom_y2 = tank.y + tank.width

            left_x = max(left_x1, left_x2)
            right_x = min(right_x1, right_x2)
            top_y = max(top_y1, top_y2)
            bottom_y = min(bottom_y1, bottom_y2)

            if left_x <= right_x and top_y <= bottom_y:
                explosion_sound.play()
                tank.score -= 1
                tank.x = random.randint(40, width - 70)
                tank.y = random.randint(40, height - 70)

            if tanks[0].score == 0:
                font1 = pygame.font.SysFont('System', 60)
                text = font1.render("Game Over :( BROWN tank won", 1, color_BROWN)
                place = text.get_rect(center=(400, 300))
                screen.blit(text, place)
                tank0.speed = 0
                tank1.speed = 0

            if tanks[1].score == 0:
                font2 = pygame.font.SysFont('System', 60)
                text = font2.render("Game Over :( BLACK tank won", 1, color_BLACK)
                place = text.get_rect(center=(400, 300))
                screen.blit(text, place)
                tank0.speed = 0
                tank1.speed = 0


def score():

    number_score_1= tanks[0].score
    number_score_2= tanks[1].score

    chet = printing_type4.render("Scores", True, color_BLACK)
    screen.blit(chet, (850, 10))

    res_tank1 = printing_type4.render("Brown tank: " + str(number_score_1), True, color_BROWN)
    power_boost1 = printing_type4.render("power: ", True, color_BROWN)
    screen.blit(res_tank1, (800,50))
    screen.blit(power_boost1, (800,90))

    res_tank2 = printing_type4.render("Black tank: " + str(number_score_2), True, color_BLACK)
    power_boost2 = printing_type4.render("power: ", True, color_BLACK)
    screen.blit(res_tank2, (800,120))
    screen.blit(power_boost2, (800,160))

    text = printing_type4.render("Game duration:", 1,  color_BLACK)
    place = text.get_rect(center = (900, 520))
    screen.blit(text, place)


Game = True

tank0 = Tank(100, 100, 2, color_BLACK, pygame.K_d, pygame.K_a, pygame.K_w, pygame.K_s, pygame.K_SPACE)
tank1 = Tank(350, 350, 2, color_BROWN)

p1 = Pulya()
p2 = Pulya()

tanks = [tank0, tank1]

pulya = [p1, p2]

w1 = Wall()
w2 = Wall()
w3 = Wall()
w4 = Wall()
w5 = Wall()
w6 = Wall()
w7 = Wall()
w8 = Wall()

walls = [w1, w2, w3, w4, w5, w6, w7, w8]

FPS = 20

clock = pygame.time.Clock()

background_image = pygame.image.load("white.png").convert()


def main_menu():
    screen = pygame.display.set_mode((width, height))

    screen.blit(background_image, [0, 0])

    pygame.display.set_caption("MAIN MENU")

    text = printing_type1.render("TANK GAME", 1, color_RED)
    place = text.get_rect(center=(501, 49))
    screen.blit(text, place)

    text = printing_type2.render("Hi man,", 1, color_BLACK)
    place = text.get_rect(center=(501, 149))
    screen.blit(text, place)

    text = printing_type2.render("What mode you wanna play?", 1, color_BLACK)
    place = text.get_rect(center=(501, 199))
    screen.blit(text, place)

    text = printing_type3.render(" PRESS 'Enter' to play SINGLE PLAYER MODE", 1, color_BLACK)
    place = text.get_rect(center=(501, 299))
    screen.blit(text, place)

    text = printing_type3.render("PRESS 'Space' to play MULTI PLAYER MODE", 1, color_BLACK)
    place = text.get_rect(center=(501, 399))
    screen.blit(text, place)

    text = printing_type3.render("PRESS 'Alt' to play MULTI PLAYER AI MODE", 1, color_BLACK)
    place = text.get_rect(center=(501, 499))
    screen.blit(text, place)

    pygame.display.flip()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            quit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                single_player()
            if event.key == pygame.K_SPACE:
                start_online_game()


def single_player():
    food = Food()

    foods = [food]

    time1 = 0
    time2 = 0
    first_timer = False
    second_timer = False
    first_power_song = False
    second_power_song = False

    running_single_player = True
    single_game_started = True
    playtime = 0

    while running_single_player:

        pygame.display.set_caption("Single player mode")
        screen = pygame.display.set_mode((width, height))
        screen.fill(color_GREEN)

        mills = clock.tick(FPS)
        if single_game_started:
            playtime = playtime + mills / 1000.0
        Playtime = printing_type4.render(str(round(playtime, 2)), True, color_BLACK)

        data_scoreboard = pygame.Surface((200, 600))

        data_scoreboard.fill((146, 172, 149))
        pygame.draw.rect(data_scoreboard, (148, 172, 149), (799, 0, 999, 699))
        screen.blit(data_scoreboard, (800, 0))
        score()
        screen.blit(Playtime, (880, 540))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    main_menu()
                    running_single_player = False
                pressed = pygame.key.get_pressed()
                for tank in tanks:
                    if event.key in tank.KEY.keys():
                        tank.change_direction(tank.KEY[event.key])
                    if event.key in tank.KEY.keys():
                        tank.move()
                    if pressed[tank.KEYPULL]:
                        bullet_shot_sound.play()
                        give_coordinates(tank)
        collision()

        for food in foods:
            for tank in tanks:
                left_x1_1 = food.x
                left_x2_1 = tank1.x

                right_x1_1 = food.x + 23
                right_x2_1 = tank1.x + tank1.width

                top_y1_1 = food.y
                top_y2_1 = tank1.y

                bottom_y1_1 = food.y + 33
                bottom_y2_1 = tank1.y + tank1.width

                left_x_1 = max(left_x1_1, left_x2_1)
                right_x_1 = min(right_x1_1, right_x2_1)
                top_y_1 = max(top_y1_1, top_y2_1)
                bottom_y_1 = min(bottom_y1_1, bottom_y2_1)

            if left_x_1 <= right_x_1 and top_y_1 <= bottom_y_1:
                first_power_song = True
                if first_power_song:
                    edaaa.play()
                    first_power_song = False
                food.status = False
                first_timer = True

        for food in foods:
            for tank in tanks:
                left_x1_2 = food.x
                left_x2_2 = tank0.x

                right_x1_2 = food.x + 23
                right_x2_2 = tank0.x + tank0.width

                top_y1_2 = food.y
                top_y2_2 = tank0.y

                bottom_y1_2 = food.y + 33
                bottom_y2_2 = tank0.y + tank0.width

                left_x_2 = max(left_x1_2, left_x2_2)
                right_x_2 = min(right_x1_2, right_x2_2)
                top_y_2 = max(top_y1_2, top_y2_2)
                bottom_y_2 = min(bottom_y1_2, bottom_y2_2)

            if left_x_2 <= right_x_2 and top_y_2 <= bottom_y_2:
                second_power_song = True
                if second_power_song:
                    edaaa.play()
                    second_power_song = False
                food.status = False
                second_timer = True

        if first_timer:
            time1 = time1 + (mills / 1000)

        if second_timer:
            time2 = time2 + (mills / 1000)

        if time1 < 5 and time1 != 0:
            tank1.speed = 4
            p2.speed = 100
            l0 = 5 - time1
            scor = "%.2f" % l0
            text = printing_type4.render(scor, True, color_BROWN)
            screen.blit(text, (890, 90))


        elif time2 < 5 and time2 != 0:
            tank0.speed = 4
            p1.speed = 100
            l0 = 5 - time2
            scor = "%.2f" % l0
            text =printing_type4.render(scor, True, color_BLACK)
            screen.blit(text, (890, 160))

        else:
            if single_game_started:
                tank0.speed = 2
                tank1.speed = 2

            food.status = True
            first_timer = False
            time1 = 0
            second_timer = False
            time2 = 0

        if tank1.score == 0:
            tank0.speed = 0
            tank1.speed = 0
            single_game_started = False
            first_timer = False
            time1 = 0
            second_timer = False
            time2 = 0
        if tank0.score == 0:
            tank0.speed = 0
            tank1.speed = 0
            game_started = False
            first_timer = False
            time1 = 0
            second_timer = False
            time2 = 0

        for i in pulya:
            i.move()
        for j in tanks:
            j.draw()
            j.move()
        for z in walls:
            z.draw()
        for f in foods:
            f.draw()
        pygame.display.flip()


while Game:
    main_menu()

pygame.quit()
