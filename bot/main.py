import telebot
from bot import config
from mongoengine import connect
from models.cats_and_products import (Texts,
                                      Category,
                                      Cart,
                                      OrdersHistory)
from bson import ObjectId
from models.user_model import User
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup

)
connect('bot_shop')

bot = telebot.TeleBot(config.TOKEN)

@bot.message_handler(commands=['start'])
def greetings(message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(*config.START_KEYBOARD.values())
    User.get_or_create_user(message)
    greetings_str = Texts.get_text('Greetings')
    bot.send_message(message.chat.id, 'HELLO!' + greetings_str, reply_markup=kb)


@bot.message_handler(func=lambda message: message.text == config.START_KEYBOARD['categories'])
def show_cats(message):
    cats_kb = InlineKeyboardMarkup()
    cats_buttons = []
    all_cats = Category.objects.all()

    for i in all_cats:
        callback_data = 'category_' + str(i.id)

        if i.is_parent:
            callback_data = 'subcategory_' + str(i.id)
        cats_buttons.append(InlineKeyboardButton(text=i.title,
                                                 callback_data=callback_data))

    cats_kb.add(*cats_buttons)
    bot.send_message(message.chat.id, text='cat example', reply_markup=cats_kb)


@bot.callback_query_handler(func=lambda call: call.data.split('_')[0] == 'subcategory')
def sub_cat(call):
    subcats_kb = InlineKeyboardMarkup()
    subcats_buttons = []
    category = Category.objects.get(id=call.data.split('_')[1])
    for i in category.sub_categories:
        callback_data = 'category_' + str(i.id)

        if i.is_parent:
            callback_data = 'subcategory_' + str(i.id)
        subcats_buttons.append(InlineKeyboardButton(text=i.title,
                                                    callback_data=callback_data))

    subcats_kb.add(*subcats_buttons)
    bot.send_message(call.message.chat.id, text='subcat example', reply_markup=subcats_kb)


@bot.callback_query_handler(func=lambda call: call.data.split('_')[0] == 'category')
def products_by_cat(call):
    cat = Category.objects.filter(id=call.data.split('_')[1]).first()
    products = cat.category_products

    if not products:
        bot.send_message(call.message.chat.id, 'В данной категории пока нет продуктов.')
    for p in products:
        products_kb = InlineKeyboardMarkup(row_width=2)
        products_kb.add(InlineKeyboardButton(
            text='Корзина',
            callback_data='addtocart_' + str(p.id)

        ),
            InlineKeyboardButton(
                text='Подробно',
                callback_data='product_' + str(p.id)
            )
        )

        title = f'<b>{p.title}</b>'
        description = f'\n\n<i>{p.description}</i>'
        bot.send_photo(call.message.chat.id,
                       p.image.get(),
                       caption=title + description,
                       reply_markup=products_kb,
                       parse_mode='HTML')


@bot.callback_query_handler(func=lambda call: call.data.split('_')[0] == 'addtocart')
def add_to_card(call):
    Cart.create_or_append_to_cart(product_id=call.data.split('_')[1],
                                  user_id=call.message.chat.id)
    cart = Cart.objects.all().first()


@bot.message_handler(func=lambda message: message.text == config.START_KEYBOARD['cart'])
def show_cart(message):
    current_user = User.objects.get(user_id=message.chat.id)
    cart = Cart.objects.filter(user=current_user, is_archived=False).first()

    if not cart:
        bot.send_message(message.chat.id, 'Корзина пустая')
        return

    if not cart.products:
        bot.send_message(message.chat.id, 'Корзина пустая')

    for product in cart.products:
        remove_kb = InlineKeyboardMarkup()
        remove_button = InlineKeyboardButton(text='Удалить продукт с корзины',
                                             callback_data='rmproduct_' + str(product.id))
        remove_kb.add(remove_button)
        bot.send_message(message.chat.id, product.title,
                         reply_markup=remove_kb)

    submit_kb = InlineKeyboardMarkup()
    submit_button = InlineKeyboardButton(
        text='Оформить заказ',
        callback_data='submit'
    )
    submit_kb.add(submit_button)
    bot.send_message(message.chat.id, 'Подтвердите Ваш заказ', reply_markup=submit_kb)



@bot.callback_query_handler(func=lambda call: call.data.split('_')[0] == 'rmproduct')
def rm_product_from_cart(call):
    current_user = User.objects.get(user_id=call.message.chat.id)
    cart = Cart.objects.get(user=current_user)
    cart.update(pull__products=ObjectId(call.data.split('_')[1]))
    bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.split('_')[0] == 'submit')
def submit_cart(call):
    current_user = User.objects.get(user_id=call.message.chat.id)
    cart = Cart.objects.filter(user=current_user, is_archived=False).first()
    cart.is_archived = True

    order_history = OrdersHistory.get_or_create(current_user)
    order_history.orders.append(cart)
    bot.send_message(call.message.chat.id, 'Спасибо за заказ!')
    cart.save()
    order_history.save()



bot.polling()


