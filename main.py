# * Entry point

from dotenv import load_dotenv

# * Main

if __name__ == "__main__":
    load_dotenv()
    import bank_analyzer.ui.app as app
    app.run()
