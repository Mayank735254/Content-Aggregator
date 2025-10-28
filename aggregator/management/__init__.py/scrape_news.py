from django.shortcuts import render, redirect, get_object_or_404
from aggregator.models import News

def news(request):
    # This is now very fast! It just reads from the database.
    # It gets all news, using the ordering from your model's Meta class.
    news_items = News.objects.all()
    context = {'news': news_items}
    # Renders the template I've provided in the next file
    return render(request, 'aggregator/news.html', context)

def urlClickTracking(request, pk):
    # Use get_object_or_404 to handle errors gracefully
    news_item = get_object_or_404(News, id=pk)
    
    # Call your property to increment the click
    news_item.track_click 
    
    # Redirect to the news item's actual link
    return redirect(news_item.link)

