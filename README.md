# Supply Chain Management System

A comprehensive web-based system for managing supply chain operations.

## Features

- Dashboard Overview
- Inventory Management
- Order Processing
- Supplier Management
- Real-time Analytics
- User Authentication
- Role-based Access Control

## Technology Stack

- React.js
- Node.js
- Express.js
- MongoDB
- Material-UI
- Redux

## Installation

1. Clone the repository:
   ```bash
   git clone git@github.com:Hirwa-Joric/Supply-Chain-Managment.git
   cd Supply-Chain-Managment
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Start the development server:
   ```bash
   npm start
   ```

## Project Structure

```
src/
├── components/     # Reusable UI components
├── pages/         # Main application pages
├── services/      # API and business logic
├── store/         # Redux store configuration
├── utils/         # Helper functions
└── App.js         # Root component
```

## Available Scripts

- `npm start`: Run the development server
- `npm test`: Run tests
- `npm run build`: Build for production
- `npm run eject`: Eject from create-react-app

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
