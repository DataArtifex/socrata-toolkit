#!/usr/bin/env ruby

require 'soda/client'

client = SODA::Client.new({:domain => "data.sfgov.org", :app_token => "YOURAPPTOKENHERE"})

results = client.get("vw6y-z8j6", :$limit => 5000)

puts "Got #{results.count} results. Dumping first results:"
results.first.each do |k, v|
  puts "#{key}: #{value}"
end