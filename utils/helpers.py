from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    """
    Helper function to build a flexible inline keyboard.
    """
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    
    if header_buttons:
        if isinstance(header_buttons, list):
            menu.insert(0, header_buttons)
        else:
            menu.insert(0, [header_buttons])
            
    if footer_buttons:
        if isinstance(footer_buttons, list):
            menu.append(footer_buttons)
        else:
            menu.append([footer_buttons])
            
    return InlineKeyboardMarkup(menu)

def get_cancel_button():
    return InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")
