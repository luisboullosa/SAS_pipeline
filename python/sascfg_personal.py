import os
import shutil

def _resolve_java_executable() -> str:
    """
    Resolves the Java 8 JRE executable dynamically:
    1. JAVA_HOME environment variable
    2. Local workspace portable java8 directory (relative to repo root)
    3. System PATH
    """
    if os.environ.get("JAVA_HOME"):
        exe_name = "java.exe" if os.name == "nt" else "java"
        cand = os.path.join(os.environ["JAVA_HOME"], "bin", exe_name)
        if os.path.exists(cand):
            return cand

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    local_candidates = [
        os.path.join(repo_root, "java8", "jdk8u422-b05-jre", "bin", "java.exe"),
        os.path.join(repo_root, "java8", "bin", "java.exe"),
        os.path.join(repo_root, "java", "bin", "java.exe"),
    ]
    for cand in local_candidates:
        if os.path.exists(cand):
            return cand

    found = shutil.which("java")
    return found if found else "java"

SAS_config_names = ['oda']

oda = {
    'java': _resolve_java_executable(),
    # Uncomment the iomhost for your specific SAS ODA region:

    # US Home Region 1
    # 'iomhost': ['odaws01-usw2.oda.sas.com', 'odaws02-usw2.oda.sas.com', 'odaws03-usw2.oda.sas.com', 'odaws04-usw2.oda.sas.com'],

    # US Home Region 2
    # 'iomhost': ['odaws01-usw2-2.oda.sas.com', 'odaws02-usw2-2.oda.sas.com'],

    # European Home Region 1 (default)
    'iomhost': ['odaws01-euw1.oda.sas.com', 'odaws02-euw1.oda.sas.com'],

    # Asia Pacific Home Region 1
    # 'iomhost': ['odaws01-apse1.oda.sas.com', 'odaws02-apse1.oda.sas.com'],

    'iomport': 8591,
    'authkey': 'oda',
    'encoding': 'utf-8'
}
