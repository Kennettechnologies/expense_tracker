# Expense Tracker

A comprehensive Django-based web application for tracking personal or business expenses with a clean and intuitive interface. Manage your finances efficiently with features like transaction management, receipt tracking, and financial insights.

![Expense Tracker Dashboard](https://via.placeholder.com/800x400?text=Expense+Tracker+Dashboard)



## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- Virtual environment (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/expense-tracker.git
   cd expense-tracker
   ```

2. **Set up a virtual environment**
   - Windows:
     ```powershell
     py -3.11 -m venv .venv

     .\.venv\Scripts\Activate.ps1
     ```
   - macOS/Linux:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the project root and add:
   ```
   DEBUG=True
   SECRET_KEY=your-secret-key-here
   ALLOWED_HOSTS=localhost,127.0.0.1
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start the development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Open `http://127.0.0.1:8000` in your browser
   - Admin interface: `http://127.0.0.1:8000/admin/`


## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Django](https://www.djangoproject.com/)
- Icons by [Feather Icons](https://feathericons.com/)
- Inspired by various personal finance tools

## 📧 Contact

Your Name - [@yourtwitter](https://twitter.com/kevin_havertz10) 

  - kevinonyangowanga@gmail.com

Project Link: https://github.com/Kennettechnologies/expense_tracker