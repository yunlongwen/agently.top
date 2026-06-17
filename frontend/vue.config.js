module.exports = {
  publicPath: '/',
  devServer: {
    host: '0.0.0.0',
    port: 3002,
    allowedHosts: 'all',
    client: {
      webSocketURL: 'wss://agently.top/ws'
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
};
