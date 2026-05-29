module.exports = {
  publicPath: '/',
  devServer: {
    host: 'localhost',
    port: 8080,
    allowedHosts: 'all',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
};
