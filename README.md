# Restaurant Inventory Management App
#### Description:
Restaurant Inventory Management App

This project is a Restaurant Inventory Management Application built with Flask and SQLite, designed to provide an accessible, lightweight system for tracking inventory, logging actions such as deliveries, sales, consumption, and waste, and visualizing data trends through interactive charts and KPI cards. The app is intended to simplify how restaurant staff manage ingredients and monitor usage, costs, and stock balances.

The system includes user authentication (registration, login/logout, password change), flexible data input via web forms and raw SQL queries, and automated reporting tools. Reports allow users to filter inventory activity by specific items and date ranges, and display meaningful KPIs such as total spend on deliveries, the latest price per unit, and the total quantity sold, consumed, or wasted.

This README provides an overview of the app’s purpose, the contents of each file, and the design decisions made during implementation.

⸻

Project Overview

Running a restaurant requires keeping a close eye on both inventory costs and usage patterns. Traditional spreadsheet-based methods often become cumbersome and error-prone, especially when dealing with multiple types of transactions like deliveries, sales, and waste.

The main goals of this project were:
 1. To simplify data entry for inventory actions by providing forms with dropdowns and file upload functionality.
 2. To track costs and usage automatically, avoiding the need for constant manual calculations.
 3. To visualize data trends through charts and KPIs so that decision-makers can quickly assess how resources are being spent and used.
 4. To implement a secure user system so that multiple users can work with the system safely, using only basic functionality such as registration, login, logout, and password management.

The design prioritizes simplicity while still offering meaningful insights into the restaurant’s operations.
Functionality
 • User Authentication:
Users can register, log in, log out, and change their password. This ensures controlled access to inventory data.
 • Inventory Logging:
Actions can be logged/deleted for items in the database, including:
 • Deliveries (incoming stock with price and quantity)
 • Sales (stock sold)
 • Consumption (kitchen usage outside of sales, e.g., staff meals or prep)
 • Waste (spoiled or discarded stock)
 • Flexible Data Entry:
Data can be entered through:
 • Web forms with dropdown menus for selecting items and action types.
 • Direct SQL queries in the SQLite database for power users or administrators.
 • File Uploads:
Bills and receipts can be uploaded and stored in the system for reference.
 • Reports and Visualizations:
Users can filter reports by item and date range to see:
 • A cumulative quantity chart by action type.
 • A stock balance chart over time.
 • KPI cards summarizing:
 1. Total spend on deliveries.
 2. Latest price per unit (calculated as price/quantity of the most recent delivery).
 3. Total quantity sold, consumed, and wasted combined.
File Descriptions
 • run.py
The main entry point for the application. This file starts the Flask server and initializes the app.
 • __init__.py
Sets up the Flask application factory and integrates extensions (such as session management). It ensures that the application is modular and organized.
 • extensions.py
Contains reusable extensions and helpers for the app, such as database connections or session utilities. Keeping this separate improves maintainability.
 • routes.py
The core of the application’s logic. This file defines all the routes for user interaction, including:
 • User authentication (login, logout, register, password change).
 • Inventory actions (logging deliveries, sales, consumption, waste).
 • Reporting and visualization logic, including SQL queries for aggregating data and generating KPIs.
 • inventory.db
The SQLite database file that stores all persistent data, including users, items, logged actions, and uploaded file references.

Raw SQL is used instead of ORM models to allow direct control over aggregation queries, simplifying reporting logic.
 • templates/
Contains all Jinja2 HTML templates for rendering web pages. Includes pages for authentication, data entry, inventory setup, inventory logs, and reports with charts and KPIs.
 • static/styles.css
The main CSS file for styling the application, ensuring consistent and clean presentation.
 • static/images/
Stores static images used in the app (e.g. an image for home pape).
 • static/upload/
Stores uploaded bills or receipts that can be linked to specific inventory actions.
Design Choices
 1. SQLite and Raw SQL:
Instead of using a heavier relational database system or an ORM like SQLAlchemy, this project uses SQLite with raw SQL queries. The choice was motivated by simplicity: SQLite requires no additional setup, and raw SQL allows for more direct aggregation queries, particularly in the reports and inventory calculations. This makes it easier to implement KPIs like “latest price per unit” or “total spend” without additional ORM abstraction layers.
 2. Minimal User Functionality:
The authentication system is intentionally simple, covering only registration, login, logout, and password changes. While more advanced role-based systems could be added, this level of functionality is sufficient for small restaurant teams.
 3. Dropdowns for Data Entry:
To minimize errors during data entry, dropdown menus are used to select items and action types. This ensures consistency and prevents typos in inventory logs.
 4. Charts and KPIs:
Data visualization is central to the project. The decision to use cumulative charts and KPIs was made to provide immediate insights into how much is being spent, how prices are trending, and how stock is being used or wasted. These metrics help managers make faster, better decisions.
