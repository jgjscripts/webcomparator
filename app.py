from flask import Flask, render_template, request
from crawler import WebCrawler
from content_processor import ContentProcessor
from comparator import ContentComparator
from crawler_pwa import PWAWebCrawler
from curl_crawler import CurlCrawler
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize components
crawler = WebCrawler()
content_processor = ContentProcessor(os.getenv('OPENAI_API_KEY'))
comparator = ContentComparator(os.getenv('OPENAI_API_KEY'))
pwa_crawler = PWAWebCrawler()
curl_crawler = CurlCrawler()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            url1 = request.form['url1']
            url2 = request.form['url2']
            use_curl = request.form.get('use_curl', False)
            
            if use_curl:
                # Generate curl commands
                curl1 = curl_crawler.get_curl_from_browser(url1)
                curl2 = curl_crawler.get_curl_from_browser(url2)
                
                # Extract content using curl
                content1 = curl_crawler.extract_content(curl1)
                content2 = curl_crawler.extract_content(curl2)
            else:
                # Auto-detect if either URL is a PWA/React site
                is_pwa1 = pwa_crawler.is_pwa_or_react(url1)
                is_pwa2 = pwa_crawler.is_pwa_or_react(url2)
                
                # Use appropriate crawler
                use_pwa_crawler = is_pwa1 or is_pwa2
                selected_crawler = pwa_crawler if use_pwa_crawler else crawler
                
                # Crawl websites
                content1 = selected_crawler.extract_content(url1)
                content2 = selected_crawler.extract_content(url2)

            if not content1 or not content2:
                return render_template('index.html', error="Failed to fetch content from one or both URLs")

            # Process contents
            processed_content1 = content_processor.prepare_content(content1)
            processed_content2 = content_processor.prepare_content(content2)

            # Compare contents (now synchronous)
            comparison_result = comparator.compare_contents(processed_content1, processed_content2)

            return render_template('index.html', 
                                comparison_result=comparison_result,
                                is_pwa1=is_pwa1 if 'is_pwa1' in locals() else None,
                                is_pwa2=is_pwa2 if 'is_pwa2' in locals() else None)

        except Exception as e:
            return render_template('index.html', error=str(e))

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True) 