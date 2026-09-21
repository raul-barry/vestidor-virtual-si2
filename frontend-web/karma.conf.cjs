module.exports = function (config) {
  config.set({
    frameworks: ['jasmine', '@angular-devkit/build-angular'],
    plugins: [require('karma-jasmine'), require('karma-chrome-launcher'), require('@angular-devkit/build-angular/plugins/karma')],
    reporters: ['progress'],
    browsers: ['ChromeHeadlessSoftware'],
    customLaunchers: {
      ChromeHeadlessSoftware: {base: 'ChromeHeadless', flags: ['--disable-gpu', '--disable-software-rasterizer', '--no-sandbox', '--disable-dev-shm-usage']}
    },
    singleRun: true,
    browserNoActivityTimeout: 60000,
    client: {jasmine: {random: false}}
  });
};
