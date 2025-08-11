
"""
Quick test script for the poker bot infrastructure.
Run this to verify everything works before production deployment.
"""

import asyncio
import sys
import os
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))

from tests.integration_test_runner import IntegrationTestRunner


async def run_quick_test():
    """Run a quick test with minimal setup."""
    print("🚀 Running quick infrastructure test...")
    

    runner = IntegrationTestRunner("sqlite+aiosqlite:///:memory:")
    
    try:
        await runner.setup()
        success = await runner.run_complete_test()
        
        if success:
            print("\n✅ SUCCESS: Infrastructure is working correctly!")
            print("🎯 Ready for production deployment.")
            return True
        else:
            print("\n❌ FAILURE: Issues detected in infrastructure.")
            print("🔧 Please check the errors above and fix before production.")
            return False
            
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await runner.cleanup()


def check_dependencies():
    """Check if all required dependencies are available."""
    print("🔍 Checking dependencies...")
    
    missing = []
    try:
        import fastapi
        print("  ✅ FastAPI")
    except ImportError:
        missing.append("fastapi")
    
    try:
        import sqlalchemy
        print("  ✅ SQLAlchemy")
    except ImportError:
        missing.append("sqlalchemy")
    
    try:
        import docker
        print("  ✅ Docker")
    except ImportError:
        missing.append("docker")
    
    try:
        import uvicorn
        print("  ✅ Uvicorn")
    except ImportError:
        missing.append("uvicorn")
    
    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        print("📦 Install with: pip install -e .")
        return False
    
    print("✅ All dependencies available")
    return True


if __name__ == "__main__":
    print("🧪 Poker Bot Infrastructure Test Script")
    print("=" * 50)
    

    if not check_dependencies():
        sys.exit(1)
    
    print("\nThis will:")
    print("• Create 4 sample bots with different strategies")
    print("• Submit them to the platform")
    print("• Run a complete tournament")
    print("• Verify all results")
    print("• Test the entire workflow end-to-end")
    
    print("\n⚠️  Note: This test uses Docker containers.")
    print("Make sure Docker is running on your system.")
    
    print("\nContinue? [y/N]: ", end="")
    try:
        response = input().strip().lower()
        if response not in ['y', 'yes']:
            print("👋 Test cancelled.")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n👋 Test cancelled.")
        sys.exit(0)
    

    success = asyncio.run(run_quick_test())
    
    if success:
        print("\n🎉 Infrastructure test completed successfully!")
        print("🚀 You can now deploy to production with confidence.")
    else:
        print("\n🔧 Please fix the issues above before production deployment.")
        sys.exit(1)