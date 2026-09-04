import { appConfig } from './app.config';

describe('application configuration', () => {
  it('registers application providers', () => {
    expect(appConfig.providers?.length).toBeGreaterThan(0);
  });
});
