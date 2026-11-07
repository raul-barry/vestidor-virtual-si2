import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { SubscriptionAdminService } from './subscription-admin.service';

describe('SubscriptionAdminService', () => {
  let service: SubscriptionAdminService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(SubscriptionAdminService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('loads available plans, current subscription, and history by organization', () => {
    service.listPlans().subscribe();
    const plans = http.expectOne('http://localhost:8000/api/subscriptions/plans');
    expect(plans.request.method).toBe('GET');
    plans.flush([]);

    service.current(12).subscribe((current) => expect(current).toBeNull());
    const current = http.expectOne('http://localhost:8000/api/platform/organizations/12/subscriptions/current');
    expect(current.request.method).toBe('GET');
    current.flush(null);

    service.history(12).subscribe();
    const history = http.expectOne('http://localhost:8000/api/platform/organizations/12/subscriptions/history');
    expect(history.request.method).toBe('GET');
    history.flush([]);
  });

  it('assigns and changes a plan with the backend request contract', () => {
    const body = { plan_id: 2 };
    service.assign(12, body).subscribe();
    let request = http.expectOne('http://localhost:8000/api/platform/organizations/12/subscriptions');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(body);
    request.flush({});

    service.change(12, body).subscribe();
    request = http.expectOne('http://localhost:8000/api/platform/organizations/12/subscriptions/current');
    expect(request.request.method).toBe('PUT');
    expect(request.request.body).toEqual(body);
    request.flush({});
  });

  it('cancels the current subscription', () => {
    service.cancel(12).subscribe();
    const request = http.expectOne('http://localhost:8000/api/platform/organizations/12/subscriptions/current/cancel');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({});
    request.flush({});
  });

  for (const status of [401, 403, 409]) {
    it(`propagates HTTP ${status} so the screen can display an authorization or conflict message`, () => {
      let received: HttpErrorResponse | undefined;
      service.current(12).subscribe({ error: (error: HttpErrorResponse) => received = error });
      http.expectOne('http://localhost:8000/api/platform/organizations/12/subscriptions/current')
        .flush({ detail: 'request rejected' }, { status, statusText: 'Request rejected' });
      expect(received?.status).toBe(status);
    });
  }
});
