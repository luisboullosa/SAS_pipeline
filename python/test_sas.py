import os
import saspy

def test_connection():
    print("Initializing SAS session using sascfg_personal.py...")
    try:
        # Assuming sascfg_personal.py is in the same directory
        cfg_path = os.path.join(os.path.dirname(__file__), 'sascfg_personal.py')
        
        # We explicitly pass the configuration file. If _authinfo is correct in ~/_authinfo, it should just work.
        sas = saspy.SASsession(cfgfile=cfg_path, cfgname='oda')
        
        print("\n===============================")
        print("SUCCESS! SAS Session Connected!")
        print("===============================\n")
        
        # Run a simple query to verify
        res = sas.submit("""
        data _null_;
            put 'Hello from SAS ODA!';
        run;
        """)
        print("SAS Log Output:")
        print(res.get('LOG', 'No log returned'))
        
        sas.disconnect()
        print("Disconnected successfully.")
        
    except Exception as e:
        print("\n!!! CONNECTION FAILED !!!")
        print(f"Error Details: {e}")
        print("\nTroubleshooting tips:")
        print("1. Is Java 8 path correct in sascfg_personal.py?")
        print("2. Is the region uncommented correctly (EU)?")
        print("3. Does your ~/_authinfo file have the exact format 'oda user <email> password <pass>'?")
        print("4. Did you accept the EULA on the SAS ODA portal recently?")

if __name__ == "__main__":
    test_connection()
