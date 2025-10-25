#include <cmath>
extern "C" {
    // Simple haversine-based ETA. Hook point to replace with H3-indexed routing.
    double eta_seconds(double lat1, double lon1, double lat2, double lon2, double speed_kmh) {
        const double R = 6371.0;
        auto rad = [](double d){ return d * M_PI / 180.0; };
        double p1 = rad(lat1), p2 = rad(lat2);
        double dp = rad(lat2 - lat1), dl = rad(lon2 - lon1);
        double a = sin(dp/2)*sin(dp/2) + cos(p1)*cos(p2)*sin(dl/2)*sin(dl/2);
        double c = 2 * atan2(sqrt(a), sqrt(1-a));
        double dist_km = R * c;
        if (speed_kmh <= 1e-6) speed_kmh = 0.001;
        double hours = dist_km / speed_kmh;
        return hours * 3600.0;
    }
}