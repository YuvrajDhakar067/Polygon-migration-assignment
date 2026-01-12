#include <iostream>
#include <iomanip>
using namespace std;

int main() {
    int t;
    cin >> t;
    
    while (t--) {
        int n;
        cin >> n;
        
        int sum = 0;
        for (int i = 0; i < n; i++) {
            int mark;
            cin >> mark;
            sum += mark;
        }
        
        double average = (double)sum / n;
        cout << fixed << setprecision(2) << average << endl;
        
        if (average >= 90) {
            cout << "A" << endl;
        } else if (average >= 80) {
            cout << "B" << endl;
        } else if (average >= 70) {
            cout << "C" << endl;
        } else if (average >= 60) {
            cout << "D" << endl;
        } else {
            cout << "F" << endl;
        }
    }
    
    return 0;
}